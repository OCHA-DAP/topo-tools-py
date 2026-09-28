"""Build the hdx/topo-tools NLD demo inputs: one folder per topo-tools tool."""

import argparse
from pathlib import Path

import duckdb
from build_nld import get

from topo_tools.api.schema_join import join
from topo_tools.api.schema_map import map as schema_map
from topo_tools.api.topo_detect import detect

SIMPLIFY_M = 100.0
SNAP_M = 0.01
# CBS StatLine "Gebieden in Nederland 2025"; Code_28/Naam_29 are its Provincies group.
GEBIEDEN = "https://opendata.cbs.nl/ODataApi/odata/86059NED/TypedDataSet?$format=json&$select=RegioS,Code_28,Naam_29"
PROVINCIEGEBIED = "https://api.pdok.nl/kadaster/bestuurlijkegebieden/ogc/v1/collections/provinciegebied/items?f=json&limit=100&crs=http://www.opengis.net/def/crs/EPSG/0/28992"


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


def simplify(con: duckdb.DuckDBPyConnection, table: str) -> None:
    coverage(con, table, f"ST_CoverageSimplify({{geoms}}, {SIMPLIFY_M}::DOUBLE)")
    # Snap only (gap width 0): removes the simplify's zero-area overlaps, keeps every water gap.
    coverage(con, table, f"ST_CoverageClean({{geoms}}, {SNAP_M}::DOUBLE, 0::DOUBLE)")


def cached(url: str, path: Path) -> Path:
    if not path.exists():
        path.write_text(get(url))
    return path


def gemeenten(src: Path, provinces: Path) -> duckdb.DuckDBPyConnection:
    """Simplified land gemeenten with provincie columns, as table `g`."""
    con = duckdb.connect()
    con.execute("LOAD spatial")
    con.execute(
        f"CREATE TABLE p AS SELECT trim(r.RegioS) AS gemeentecode, trim(r.Code_28) AS provinciecode, "
        f"trim(r.Naam_29) AS provincienaam FROM (SELECT unnest(value) AS r FROM read_json('{provinces}'))"
    )
    con.execute(
        f"CREATE TABLE t AS SELECT row_number() OVER (ORDER BY gemeentecode) AS i, * EXCLUDE (bbox) "
        f"FROM read_parquet('{src}') WHERE water = 'NEE'"
    )
    simplify(con, "t")
    missing = con.execute(
        "SELECT count(*) FROM t ANTI JOIN p USING (gemeentecode)"
    ).fetchone()[0]
    if missing:
        msg = f"{missing} gemeenten missing from the provincie lookup"
        raise SystemExit(msg)
    con.execute("CREATE TABLE g AS SELECT * FROM t JOIN p USING (gemeentecode)")
    return con


def copy(con: duckdb.DuckDBPyConnection, query: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY ({query}) TO '{out}' (FORMAT parquet, COMPRESSION zstd)")


def schema_map_input(con: duckdb.DuckDBPyConnection, out: Path) -> None:
    copy(
        con,
        "SELECT geometry, gemeentecode, gemeentenaam, provinciecode, provincienaam, "
        "'NL' AS landcode, 'Nederland' AS landnaam, water, jaar "
        "FROM g ORDER BY gemeentecode",
        out,
    )


def schema_join_child(con: duckdb.DuckDBPyConnection, out: Path) -> None:
    copy(
        con,
        "SELECT geometry, gemeentecode AS adm2_code, gemeentenaam AS adm2_name "
        "FROM g ORDER BY adm2_code",
        out,
    )


def schema_join_parent(provinciegebied: Path, out: Path) -> None:
    con = duckdb.connect()
    con.execute("LOAD spatial")
    con.execute(
        "CREATE TABLE t AS SELECT row_number() OVER (ORDER BY identificatie) AS i, geom AS geometry, identificatie, naam "
        f"FROM ST_Read('{provinciegebied}')"
    )
    simplify(con, "t")
    copy(
        con,
        "SELECT geometry, identificatie AS adm1_code, naam AS adm1_name FROM t ORDER BY adm1_code",
        out,
    )


def overlaps(path: Path, cache: Path) -> int:
    issues = cache / f"{path.parent.name}_{path.stem}_issues.parquet"
    detect(path, issues, tmp_dir=cache / "tmp")
    return duckdb.sql(
        f"SELECT count(*) FROM read_parquet('{issues}') WHERE kind = 'overlap'"
    ).fetchone()[0]


def join_issues(child: Path, parent: Path, cache: Path) -> int:
    out = cache / "schema-join" / "nld_admin2_join.parquet"
    join(child, parent, out, tmp_dir=cache / "tmp")
    issues = out.with_stem(out.stem + "_issues")
    if not issues.exists():
        return 0
    return duckdb.sql(f"SELECT count(*) FROM read_parquet('{issues}')").fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog", type=Path, required=True, help="Catalog root directory"
    )
    parser.add_argument("--cache", type=Path, default=Path("tmp/catalog/cache/demo"))
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)

    src = args.catalog / "nld" / "2025" / "nld_admin2" / "nld_admin2.parquet"
    demo = args.catalog / "nld" / "demo"
    raw = demo / "schema-map" / "nld_admin2.parquet"
    child = demo / "schema-join" / "nld_admin2.parquet"
    parent = demo / "schema-join" / "nld_admin1.parquet"
    mapped = args.cache / "schema-map" / "nld_admin2_mapped.parquet"

    con = gemeenten(src, cached(GEBIEDEN, args.cache / "gebieden_2025.json"))
    schema_map_input(con, raw)
    schema_join_child(con, child)
    schema_join_parent(
        cached(PROVINCIEGEBIED, args.cache / "provinciegebied.json"), parent
    )
    for path in (raw, child, parent):
        if n := overlaps(path, args.cache):
            msg = f"{path}: {n} overlaps after simplify and clean"
            raise SystemExit(msg)
    schema_map(
        raw,
        mapped,
        csv_output=mapped.with_name("nld_admin2_crosswalk.csv"),
        tmp_dir=args.cache / "tmp",
    )
    if n := join_issues(child, parent, args.cache):
        msg = f"schema-join reported {n} issues"
        raise SystemExit(msg)


if __name__ == "__main__":
    main()
