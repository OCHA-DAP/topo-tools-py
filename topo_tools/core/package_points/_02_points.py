"""Dissolves each detected level and reduces it to a pole-of-inaccessibility point."""

from duckdb import DuckDBPyConnection

from topo_tools.core.dissolve import _02_dissolve as dissolve_stage
from topo_tools.core.schema_map._target_schema import TargetSchema


def _check_row_count(
    conn: DuckDBPyConnection, dissolved: str, source: str, code_column: str
) -> None:
    dissolved_count = conn.execute(f'SELECT COUNT(*) FROM "{dissolved}"').fetchone()[0]
    distinct_count = conn.execute(
        f'SELECT COUNT(DISTINCT "{code_column}") FROM "{source}"'
    ).fetchone()[0]
    if dissolved_count != distinct_count:
        msg = (
            f"{dissolved}: {dissolved_count} dissolved row(s) but "
            f"{distinct_count} distinct {code_column!r} value(s) in {source}"
        )
        raise ValueError(msg)


def _check_covers(conn: DuckDBPyConnection, dissolved: str, points: str) -> None:
    uncovered = conn.execute(f"""--sql
        SELECT COUNT(*) FROM "{dissolved}" d
        JOIN "{points}" p USING (fid)
        WHERE NOT ST_Covers(d.geom, p.geom)
    """).fetchone()[0]
    if uncovered:
        msg = f"{points}: {uncovered} label point(s) not covered by their own polygon"
        raise ValueError(msg)


def main(
    conn: DuckDBPyConnection,
    name: str,
    levels: list[int],
    schema: TargetSchema,
    depth_column: str,
) -> None:
    """Dissolve `{name}_01` per level and union its label points into `{name}_02`.

    Combined via `UNION ALL BY NAME`: coarser levels keep fewer columns.
    """
    columns = [row[0] for row in conn.execute(f'DESCRIBE "{name}_01"').fetchall()]
    if depth_column in columns:
        table_in = f"{name}_01"
        msg = f"depth_column {depth_column!r} already exists on {table_in!r}"
        raise ValueError(msg)

    point_tables = []
    for n in levels:
        code_column = schema.code_field.format(n=n)
        dissolved = f"{name}_02_tmp{n}"
        dissolve_stage.main(
            conn,
            f"{name}_01",
            dissolved,
            group_by=[code_column],
            target_schema=schema,
        )
        _check_row_count(conn, dissolved, f"{name}_01", code_column)

        points = f"{name}_02_pts{n}"
        conn.execute(f"""--sql
            CREATE OR REPLACE TABLE "{points}" AS
            SELECT * EXCLUDE (geom), {n} AS "{depth_column}",
                   (ST_MaximumInscribedCircle(geom)).center AS geom
            FROM "{dissolved}"
        """)
        _check_covers(conn, dissolved, points)
        conn.execute(f'DROP TABLE IF EXISTS "{dissolved}"')
        point_tables.append(points)

    union_sql = " UNION ALL BY NAME ".join(f'SELECT * FROM "{t}"' for t in point_tables)
    conn.execute(f'CREATE OR REPLACE TABLE "{name}_02" AS {union_sql}')
    for t in point_tables:
        conn.execute(f'DROP TABLE IF EXISTS "{t}"')
