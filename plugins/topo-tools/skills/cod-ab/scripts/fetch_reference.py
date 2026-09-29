# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "duckdb",
#     "tenacity",
# ]
# ///
"""Fetch the previous COD-AB release from source.coop into 00a_old/.

Standalone (PEP 723) script, run with uv:

    uv run <skill-dir>/scripts/fetch_reference.py <iso3>

Reads the highest `vNN` under `matched/{iso3}/` in the hdx/cod-ab catalog on
source.coop, writes each of its `{iso3}_admin{n}.parquet` layers plus
`{iso3}_admin0.parquet` (a dissolve of its admin1) to
02_working/{iso3}/{version}/00a_old/, and prints the old/new version numbers.
With no release there, prints ref_version=none version=v01 and exits cleanly.
"""

import argparse
import json
import logging
import re
import urllib.error
import urllib.request
from http import HTTPStatus
from pathlib import Path

import duckdb
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logging.basicConfig(format="%(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

_CATALOG = "https://data.source.coop/hdx/cod-ab/matched"
_COPY_OPTIONS = (
    "FORMAT PARQUET, COMPRESSION ZSTD, COMPRESSION_LEVEL 15, GEOPARQUET_VERSION 'V2'"
)
_VERSION_RE = re.compile(r"^\./(v\d+)/catalog\.json$")
_ADMIN0_COLUMNS = re.compile(r"^(adm0_.*|iso2|iso3|lang\d*|valid_on|valid_to|version)$")


class _NotFoundError(Exception):
    pass


@retry(
    retry=retry_if_not_exception_type(_NotFoundError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, max=20),
    reraise=True,
)
def _get_json(url: str) -> dict:
    # source.coop answers 403 to urllib's default Python-urllib user agent.
    request = urllib.request.Request(url, headers={"User-Agent": "topo-tools-cod-ab"})  # noqa: S310 (hardcoded https catalog)
    try:
        with urllib.request.urlopen(request) as resp:  # noqa: S310 (hardcoded https catalog)
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == HTTPStatus.NOT_FOUND:
            raise _NotFoundError(url) from e
        raise


def _child_hrefs(catalog: dict) -> list[str]:
    return [link["href"] for link in catalog["links"] if link["rel"] == "child"]


def latest_version(iso3: str) -> str | None:
    """Return the highest vNN published under matched/{iso3}/, or None."""
    try:
        catalog = _get_json(f"{_CATALOG}/{iso3}/catalog.json")
    except _NotFoundError:
        return None
    versions = [m[1] for h in _child_hrefs(catalog) if (m := _VERSION_RE.match(h))]
    return max(versions, key=lambda v: int(v[1:]), default=None)


def layer_urls(iso3: str, version: str) -> dict[str, str]:
    """Map each layer name (afg_admin1) to its GeoParquet URL."""
    base = f"{_CATALOG}/{iso3}/{version}"
    urls = {}
    for href in _child_hrefs(_get_json(f"{base}/catalog.json")):
        layer = href.removeprefix("./").split("/")[0]
        collection = _get_json(f"{base}/{layer}/collection.json")
        data = collection["assets"][layer]["href"].removeprefix("./")
        urls[layer] = f"{base}/{layer}/{data}"
    return urls


def increment_version(version: str) -> str:
    """Increment the version number: 'v02' -> 'v03'."""
    return f"v{int(version[1:]) + 1:02d}"


def write_layer(con: duckdb.DuckDBPyConnection, url: str, dst: Path) -> None:
    """Copy one remote layer to dst, geometry first."""
    con.execute(f"""
        COPY (SELECT geometry, * EXCLUDE (geometry) FROM read_parquet('{url}'))
        TO '{dst}' ({_COPY_OPTIONS})
    """)
    count = con.execute(f"SELECT COUNT(*) FROM '{dst}'").fetchone()[0]
    log.info("  %s: %s features", dst.name, f"{count:,}")


def write_admin0(con: duckdb.DuckDBPyConnection, admin1: Path, dst: Path) -> None:
    """Dissolve admin1 into one admin0 feature, keeping its country-wide columns."""
    columns = [
        r[0] for r in con.execute(f"DESCRIBE SELECT * FROM '{admin1}'").fetchall()
    ]
    kept = ", ".join(
        f'any_value("{c}") AS "{c}"' for c in columns if _ADMIN0_COLUMNS.match(c)
    )
    con.execute(f"""
        COPY (SELECT ST_Union_Agg(geometry) AS geometry, {kept} FROM '{admin1}')
        TO '{dst}' ({_COPY_OPTIONS})
    """)
    log.info("  %s: dissolved from %s", dst.name, admin1.name)


def main() -> None:
    """Fetch the previous release for one ISO3 into 00a_old/."""
    parser = argparse.ArgumentParser(
        description="Fetch the previous COD-AB release from source.coop.",
    )
    parser.add_argument("iso3", help="Country ISO3 code (e.g. syr)")
    parser.add_argument(
        "--working-dir", type=Path, default=Path("02_working"), help="Working tier root"
    )
    args = parser.parse_args()
    iso3 = args.iso3.lower()

    ref_version = latest_version(iso3)
    if ref_version is None:
        log.info("No release for %s under %s.", iso3, _CATALOG)
        log.info("ref_version=none version=v01")
        return
    new_version = increment_version(ref_version)
    log.info("Old: %s  New: %s\n", ref_version, new_version)

    old_dir = args.working_dir / iso3 / new_version / "00a_old"
    old_dir.mkdir(parents=True, exist_ok=True)
    log.info("Old -> %s/", old_dir)
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial; INSTALL httpfs; LOAD httpfs;")
    try:
        for layer, url in sorted(layer_urls(iso3, ref_version).items()):
            write_layer(con, url, old_dir / f"{layer}.parquet")
        admin1 = old_dir / f"{iso3}_admin1.parquet"
        if admin1.exists():
            write_admin0(con, admin1, old_dir / f"{iso3}_admin0.parquet")
    finally:
        con.close()

    log.info("ref_version=%s version=%s", ref_version, new_version)


if __name__ == "__main__":
    main()
