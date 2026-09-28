"""Build the hdx/topo-tools NLD demo tiers: one input per topo-tools step, each built from the step before."""

import argparse
from pathlib import Path

import duckdb

from topo_tools.api.schema_crosswalk import crosswalk
from topo_tools.api.topo_detect import detect

SIMPLIFY_M = 100.0
SNAP_M = 0.01


def coverage(con: duckdb.DuckDBPyConnection, table: str, call: str) -> None:
    """Replace `table`'s geometry with a coverage function's per-row result, keyed by `i`."""
    con.execute(f"""
        CREATE OR REPLACE TABLE {table} AS
        WITH parts AS (
            SELECT unnest(ST_Dump({call.format(geoms="list(geometry::GEOMETRY ORDER BY i)")})) AS d
            FROM {table}
        ), merged AS (
            SELECT d.path[1] AS i, ST_Union_Agg(d.geom) AS geometry FROM parts GROUP BY 1
        )
        SELECT t.i, m.geometry::GEOMETRY('EPSG:28992') AS geometry, t.* EXCLUDE (i, geometry)
        FROM {table} t JOIN merged m USING (i)
    """)


def admin2_simplified_raw(src: Path, out: Path) -> None:
    con = duckdb.connect()
    con.execute("LOAD spatial")
    con.execute(
        f"CREATE TABLE t AS SELECT row_number() OVER (ORDER BY gemeentecode) AS i, * EXCLUDE (bbox) "
        f"FROM read_parquet('{src}') WHERE water = 'NEE'"
    )
    coverage(con, "t", f"ST_CoverageSimplify({{geoms}}, {SIMPLIFY_M}::DOUBLE)")
    # Snap only (gap width 0): removes the simplify's zero-area overlaps, keeps every water gap.
    coverage(con, "t", f"ST_CoverageClean({{geoms}}, {SNAP_M}::DOUBLE, 0::DOUBLE)")
    out.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"COPY (SELECT geometry, * EXCLUDE (i, geometry) FROM t ORDER BY gemeentecode) "
        f"TO '{out}' (FORMAT parquet, COMPRESSION zstd)"
    )


def overlaps(path: Path, cache: Path) -> int:
    issues = cache / f"{path.parent.name}_{path.stem}_issues.parquet"
    detect(path, issues, tmp_dir=cache / "tmp")
    return duckdb.sql(
        f"SELECT count(*) FROM read_parquet('{issues}') WHERE kind = 'overlap'"
    ).fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog", type=Path, required=True, help="Catalog root directory"
    )
    parser.add_argument("--cache", type=Path, default=Path("tmp/catalog/cache/demo"))
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)

    src = args.catalog / "nld" / "2025" / "nld_admin2" / "nld_admin2.parquet"
    tier = args.catalog / "nld" / "demo" / "admin2-simplified"
    raw = tier / "00_raw" / "nld_admin2_raw.parquet"
    mapped = tier / "01_mapped" / "nld_admin2_mapped.parquet"

    admin2_simplified_raw(src, raw)
    if n := overlaps(raw, args.cache):
        msg = f"{raw}: {n} overlaps after simplify and clean"
        raise SystemExit(msg)
    crosswalk(
        raw,
        mapped,
        mapped.with_name("nld_admin2_crosswalk.csv"),
        level=2,
        tmp_dir=args.cache / "tmp",
    )


if __name__ == "__main__":
    main()
