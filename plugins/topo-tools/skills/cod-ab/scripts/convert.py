# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "duckdb",
#     "pyogrio",
# ]
# ///
"""Convert source layers to GeoParquet, or GeoParquet layers to one candidate GDB.

uv run <skill-dir>/scripts/convert.py to-parquet <src> <dst-dir>
uv run <skill-dir>/scripts/convert.py to-gdb <out.gdb> [<name>=]<layer.parquet>...
"""

import argparse
import json
import logging
import re
import sys
import unicodedata
from pathlib import Path

import duckdb
import numpy as np
import pyogrio.raw
from fetch_reference import convert_layer, get_layers

logging.basicConfig(format="%(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

_COPY_OPTIONS = (
    "FORMAT PARQUET, COMPRESSION ZSTD, COMPRESSION_LEVEL 15, GEOPARQUET_VERSION 'V2'"
)
_CHUNK_SIZE = 10_000
_GDB_LAYER_OPTIONS = {"TARGET_ARCGIS_VERSION": "ARCGIS_PRO_3_2_OR_LATER"}


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    return con


def _sql_str(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _ascii_name(name: str) -> str:
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()


def _source_counts(con: duckdb.DuckDBPyConnection, src: Path) -> dict[str, int]:
    """Layer name to feature count, from GDAL's own metadata."""
    (layers,) = con.execute(
        f"SELECT layers FROM ST_Read_Meta({_sql_str(src)})"
    ).fetchone()
    return {layer["name"]: layer["feature_count"] for layer in layers}


def to_parquet(src: Path, dst_dir: Path) -> None:
    """Convert every layer of src to GeoParquet, raising on a feature-count mismatch."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    con = _connect()
    is_gdb = src.suffix.lower() == ".gdb"
    counts = {} if is_gdb else _source_counts(con, src)
    layers = get_layers(src) if is_gdb else list(counts)
    mismatches = []
    for layer in layers:
        stem = layer if len(layers) > 1 or is_gdb else src.stem
        dst = dst_dir / f"{_ascii_name(stem)}.parquet"
        if dst.exists():
            sys.exit(f"Refusing to overwrite {dst}")
        if is_gdb:
            # DuckDB's ST_Read returns 0 rows on Esri-authored GDBs.
            convert_layer(con, src, layer, dst)
            expected = pyogrio.read_info(str(src), layer=layer)["features"]
        else:
            read = f"ST_Read({_sql_str(src)}, layer={_sql_str(layer)})"
            # ST_Read keeps the source's own geometry column name, e.g. a GPKG's.
            geom = next(
                (
                    name
                    for name, type_, *_ in con.execute(
                        f"DESCRIBE FROM {read}"
                    ).fetchall()
                    if type_.startswith("GEOMETRY")
                ),
                None,
            )
            if geom is None:
                log.info("%s: skipped, no geometry column", layer)
                continue
            con.execute(
                f'COPY (SELECT "{geom}" AS geometry, * EXCLUDE ("{geom}") '
                f"FROM {read}) TO {_sql_str(dst)} ({_COPY_OPTIONS})"
            )
            expected = counts[layer]
        (written,) = con.execute(f"SELECT count(*) FROM {_sql_str(dst)}").fetchone()
        log.info("%s: source %s, written %s", dst.name, expected, written)
        if written != expected:
            mismatches.append(dst.name)
    if mismatches:
        sys.exit(f"Feature-count mismatch: {', '.join(mismatches)}")


def _parquet_crs(con: duckdb.DuckDBPyConnection, path: Path) -> str:
    """Return the geometry CRS from GeoParquet metadata, EPSG:4326 when absent."""
    row = con.execute(
        f"SELECT decode(value) FROM parquet_kv_metadata({_sql_str(path)}) "
        "WHERE decode(key) = 'geo'"
    ).fetchone()
    crs = json.loads(row[0])["columns"]["geometry"].get("crs") if row else None
    return json.dumps(crs) if crs else "EPSG:4326"


def _geometry_type(con: duckdb.DuckDBPyConnection, path: Path) -> str | None:
    """Return the single type every feature is promoted to, None with no geometry."""
    columns = [
        c for (c, *_) in con.execute(f"DESCRIBE FROM {_sql_str(path)}").fetchall()
    ]
    if "geometry" not in columns:
        return None
    types = {
        t.removeprefix("MULTI")
        for (t,) in con.execute(
            f"SELECT DISTINCT ST_GeometryType(geometry)::VARCHAR FROM {_sql_str(path)} "
            "WHERE geometry IS NOT NULL"
        ).fetchall()
    }
    if len(types) > 1:
        sys.exit(f"{path.name}: mixed geometry types {sorted(types)}")
    if not types:
        return None
    return {"POLYGON": "MultiPolygon", "LINESTRING": "MultiLineString"}.get(
        types.pop(), "Point"
    )


def to_gdb(out: Path, layers: list[str]) -> None:
    """Write each `[name=]path` GeoParquet file as one FileGDB layer, in row order."""
    if out.exists():
        sys.exit(f"Refusing to overwrite {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    con = _connect()
    for arg in layers:
        name, _, path_str = arg.rpartition("=")
        path = Path(path_str)
        name = name or path.stem
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            sys.exit(f"Invalid FileGDB layer name {name!r}: start with a letter")
        geometry_type = _geometry_type(con, path)
        columns = [
            c for (c, *_) in con.execute(f"DESCRIBE FROM {_sql_str(path)}").fetchall()
        ]
        exclude = (
            "geometry, file_row_number" if "geometry" in columns else "file_row_number"
        )
        geom_sql = ", ST_AsWKB(geometry) AS _geom_wkb" if geometry_type else ""
        (total,) = con.execute(f"SELECT count(*) FROM {_sql_str(path)}").fetchone()
        for offset in range(0, total, _CHUNK_SIZE):
            chunk = con.execute(
                f"SELECT * EXCLUDE ({exclude}){geom_sql} "
                f"FROM read_parquet({_sql_str(path)}, file_row_number = true) "
                f"WHERE file_row_number >= {offset} "
                f"AND file_row_number < {offset + _CHUNK_SIZE} "
                f"ORDER BY file_row_number"
            ).fetchnumpy()
            geometry = None
            if geometry_type:
                wkb = chunk.pop("_geom_wkb")
                geometry = np.array(
                    [
                        None if m else bytes(g)
                        for g, m in zip(
                            np.ma.getdata(wkb), np.ma.getmaskarray(wkb), strict=True
                        )
                    ],
                    object,
                )
            fields = list(chunk)
            pyogrio.raw.write(
                str(out),
                geometry,
                [np.ma.getdata(chunk[f]) for f in fields],
                fields,
                field_mask=[np.ma.getmaskarray(chunk[f]) for f in fields],
                layer=name,
                driver="OpenFileGDB",
                geometry_type=geometry_type,
                crs=_parquet_crs(con, path) if geometry_type else None,
                promote_to_multi=geometry_type not in (None, "Point"),
                append=offset > 0,
                layer_options=_GDB_LAYER_OPTIONS,
            )
        info = pyogrio.read_info(str(out), layer=name)
        log.info("%s: source %s, written %s", name, total, info["features"])
        if info["features"] != total:
            sys.exit(f"Feature-count mismatch: {name}")


def main() -> None:
    """Dispatch the to-parquet/to-gdb subcommands."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("to-parquet", help="SHP/GPKG/GeoJSON/GDB to GeoParquet")
    p.add_argument("src", type=Path)
    p.add_argument("dst_dir", type=Path)
    g = sub.add_parser("to-gdb", help="GeoParquet layers to one FileGDB")
    g.add_argument("out", type=Path)
    g.add_argument("layers", nargs="+", metavar="[NAME=]PARQUET")
    args = parser.parse_args()
    if args.command == "to-parquet":
        to_parquet(args.src, args.dst_dir)
    else:
        to_gdb(args.out, args.layers)


if __name__ == "__main__":
    main()
