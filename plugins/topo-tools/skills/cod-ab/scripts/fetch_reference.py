# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "duckdb",
#     "pyogrio",
# ]
# ///
"""Fetch the HDX COD-AB reference GDB and convert it to GeoParquet.

Standalone (PEP 723) script, run with uv:

    uv run <skill-dir>/scripts/fetch_reference.py <iso3>

Downloads the GDB from HDX, converts all layers to GeoParquet in
02_working/{iso3}/{version}/00a_old/, and prints the old/new version numbers.
The GDB is deleted after conversion. With no HDX release, prints
ref_version=none version=v01 and exits cleanly. Reads every layer through
pyogrio in bounded chunks (never DuckDB's own ST_Read on the raw GDB, which
silently returns 0 rows on real HDX GDBs) and accumulates each chunk into a
file-backed DuckDB table, so peak Python memory is one chunk, not the whole
layer.
"""

import argparse
import json
import logging
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from http import HTTPStatus
from pathlib import Path

import duckdb
import numpy as np
import pyogrio
import pyogrio.raw

logging.basicConfig(format="%(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

_HDX_API = "https://data.humdata.org/api/3/action/package_show?id=cod-ab-{iso3}"
_COPY_OPTIONS = (
    "FORMAT PARQUET, COMPRESSION ZSTD, COMPRESSION_LEVEL 15, GEOPARQUET_VERSION 'V2'"
)
_CHUNK_SIZE = 10_000
_DTYPE_KIND_TO_SQL = {
    "O": "VARCHAR",
    "i": "BIGINT",
    "u": "BIGINT",
    "f": "DOUBLE",
    "b": "BOOLEAN",
    "M": "TIMESTAMP",
}


def download_gdb(iso3: str, country_dir: Path) -> Path | None:
    """Download and extract the HDX COD-AB GDB. Returns None if HDX has none."""
    url = _HDX_API.format(iso3=iso3)
    log.info("Querying HDX for cod-ab-%s...", iso3)
    try:
        with urllib.request.urlopen(url) as resp:  # noqa: S310 (url is the hardcoded HDX API, always https)
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == HTTPStatus.NOT_FOUND:
            return None
        raise

    if not data.get("success"):
        return None

    resources = data["result"]["resources"]
    gdb_resources = [
        r
        for r in resources
        if r.get("format", "").lower() == "geodatabase"
        or ".gdb" in r.get("name", "").lower()
    ]
    if not gdb_resources:
        return None

    resource = gdb_resources[0]
    download_url = resource["url"]
    if not download_url.startswith("https://"):
        sys.exit(f"Refusing non-https HDX download URL: {download_url}")
    zip_name = resource["name"]
    zip_path = country_dir / zip_name

    log.info("Downloading %s...", zip_name)
    urllib.request.urlretrieve(download_url, zip_path)  # noqa: S310 (scheme validated above)

    log.info("Extracting...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        resolved_root = country_dir.resolve()
        for member in zf.namelist():
            if not (resolved_root / member).resolve().is_relative_to(resolved_root):
                sys.exit(f"Refusing zip member outside extraction dir: {member}")
        zf.extractall(country_dir)
    zip_path.unlink()

    gdbs = list(country_dir.glob("**/*.gdb"))
    if not gdbs:
        sys.exit("Extracted zip but no .gdb found, check the HDX resource")
    return gdbs[0]


def get_layers(path: Path) -> list[str]:
    """Return layer names from a spatial archive."""
    return [name for name, _geom_type in pyogrio.list_layers(str(path))]


def get_version(path: Path, layers: list[str]) -> str:
    """Read the version field from the first layer that has one."""
    for layer in layers:
        info = pyogrio.read_info(str(path), layer=layer)
        if "version" not in info["fields"]:
            continue
        _meta, _fids, _geometry, field_data = pyogrio.raw.read(
            str(path),
            layer=layer,
            columns=["version"],
            read_geometry=False,
            max_features=1,
        )
        (version_field,) = field_data
        if len(version_field) and version_field[0] is not None:
            return version_field[0]
    sys.exit(f"Could not detect version from {path}")


def normalize_version(version: str) -> str:
    """Normalize version string to 'vNN' form: 'V_01' → 'v01', 'v02' → 'v02'."""
    cleaned = version.lower().lstrip("v").lstrip("_").replace("_", ".")
    major = int(cleaned.split(".")[0])
    return f"v{major:02d}"


def increment_version(version: str) -> str:
    """Increment the major version number: 'v02' → 'v03', 'V_01' → 'v02'."""
    cleaned = version.lower().lstrip("v").lstrip("_").replace("_", ".")
    major = int(cleaned.split(".")[0])
    return f"v{major + 1:02d}"


def _field_sql_types(path: Path, layer: str) -> dict[str, str]:
    """Map each field name to its DuckDB SQL type.

    Read from the layer's own field definitions, never inferred from a chunk.
    """
    info = pyogrio.read_info(str(path), layer=layer)
    return {
        name: _DTYPE_KIND_TO_SQL.get(np.dtype(dtype).kind, "VARCHAR")
        for name, dtype in zip(info["fields"], info["dtypes"], strict=True)
    }


def _read_chunk(gdb_path: Path, layer: str, offset: int) -> tuple[dict, int]:
    """Read up to _CHUNK_SIZE features as a dict of numpy arrays (geometry as WKB).

    Drops any field that's entirely NULL in this chunk: DuckDB's numpy
    registration errors on a large all-NULL object array.
    """
    meta, _fids, geometry, field_data = pyogrio.raw.read(
        str(gdb_path), layer=layer, skip_features=offset, max_features=_CHUNK_SIZE
    )
    cols = {}
    for name, raw_arr in zip(meta["fields"], field_data, strict=True):
        if raw_arr.dtype.kind == "M":
            cols[name] = raw_arr.astype("datetime64[us]")
        elif raw_arr.dtype == object and all(v is None for v in raw_arr):
            continue
        else:
            cols[name] = raw_arr
    cols["_geom_wkb"] = geometry
    return cols, len(geometry)


def convert_layer(
    con: duckdb.DuckDBPyConnection, gdb_path: Path, layer: str, dst: Path
) -> None:
    """Convert one layer to GeoParquet via chunked pyogrio reads + DuckDB writes."""
    if dst.exists():
        row = con.execute(f"SELECT COUNT(*) FROM '{dst}'").fetchone()
        count = row[0] if row else 0
        log.info("  skip %s (exists, %s features)", dst.name, f"{count:,}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)

    field_types = _field_sql_types(gdb_path, layer)
    table = f"_convert_{layer}"
    con.execute(f"DROP TABLE IF EXISTS {table}")
    cols_sql = ", ".join(
        f'"{name}" {sql_type}' for name, sql_type in field_types.items()
    )
    con.execute(f"CREATE TABLE {table} (geometry GEOMETRY, {cols_sql})")

    offset, total = 0, 0
    while True:
        cols, n = _read_chunk(gdb_path, layer, offset)
        if n == 0:
            break
        con.register("_chunk", cols)
        select_list = ["ST_GeomFromWKB(_geom_wkb) AS geometry"] + [
            f'"{name}"' if name in cols else f'NULL::{sql_type} AS "{name}"'
            for name, sql_type in field_types.items()
        ]
        con.execute(f"INSERT INTO {table} SELECT {', '.join(select_list)} FROM _chunk")
        con.unregister("_chunk")
        total += n
        offset += _CHUNK_SIZE

    con.execute(f"COPY {table} TO '{dst}' ({_COPY_OPTIONS})")
    con.execute(f"DROP TABLE {table}")
    log.info("  %s: %s features", dst.name, f"{total:,}")


def main() -> None:
    """Fetch the HDX release for one ISO3 and convert it into 00a_old/."""
    parser = argparse.ArgumentParser(
        description="Fetch HDX COD-AB release GDB and convert to GeoParquet.",
    )
    parser.add_argument("iso3", help="Country ISO3 code (e.g. syr)")
    parser.add_argument(
        "--working-dir", type=Path, default=Path("02_working"), help="Working tier root"
    )
    args = parser.parse_args()
    iso3 = args.iso3.lower()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        gdb = download_gdb(iso3, tmp_dir)
        if gdb is None:
            log.info("No HDX release for cod-ab-%s.", iso3)
            log.info("ref_version=none version=v01")
            return

        layers = get_layers(gdb)
        ref_version = normalize_version(get_version(gdb, layers))
        new_version = increment_version(ref_version)
        log.info("Old: %s  New: %s\n", ref_version, new_version)

        old_dir = args.working_dir / iso3 / new_version / "00a_old"
        con = duckdb.connect(str(tmp_dir / "fetch_reference.duckdb"))
        con.execute("INSTALL spatial; LOAD spatial;")
        log.info("Old -> %s/", old_dir)
        try:
            for layer in layers:
                convert_layer(con, gdb, layer, old_dir / f"{layer}.parquet")
        finally:
            con.close()

    log.info("ref_version=%s version=%s", ref_version, new_version)


if __name__ == "__main__":
    main()
