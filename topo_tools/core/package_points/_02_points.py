"""Dissolves each detected level and reduces it to a pole-of-inaccessibility point."""

from duckdb import DuckDBPyConnection

from topo_tools.core.dissolve import _02_dissolve as dissolve_stage
from topo_tools.core.schema_map._level_columns import (
    LevelColumns,
    detect_level_columns_or_single,
    verify_functional_cluster,
)
from topo_tools.core.schema_map._target_schema import TargetSchema


def _check_row_count(
    conn: DuckDBPyConnection, dissolved: str, source: str, group_by: list[str]
) -> None:
    dissolved_count = conn.execute(f'SELECT COUNT(*) FROM "{dissolved}"').fetchone()[0]
    if not group_by:
        distinct_count = 1
    else:
        group_by_sql = ", ".join(f'"{c}"' for c in group_by)
        distinct_count = conn.execute(
            f'SELECT COUNT(DISTINCT ({group_by_sql})) FROM "{source}"'
        ).fetchone()[0]
    if dissolved_count != distinct_count:
        msg = (
            f"{dissolved}: {dissolved_count} dissolved row(s) but "
            f"{distinct_count} distinct {group_by!r} value(s) in {source}"
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


def _level_group_by(
    schema: TargetSchema | None,
    level_columns: dict[int, LevelColumns] | None,
    n: int,
) -> tuple[list[str], list[str]]:
    """One level's dissolve group_by/exclude, from an explicit schema or auto-detect."""
    if schema is not None:
        return [schema.code_field.format(n=n)], []

    cluster = level_columns[n]
    if not cluster.group_by and len(level_columns) > 1:
        msg = f"no reliable group-by column detected for level {n}"
        raise ValueError(msg)
    exclude = [
        c
        for lvl, cols in level_columns.items()
        if lvl > n
        for c in cols.identity_columns
    ]
    return cluster.group_by, exclude


def main(
    conn: DuckDBPyConnection,
    name: str,
    levels: list[int],
    schema: TargetSchema | None,
    depth_column: str,
) -> None:
    """Dissolve `{name}_01` per level and union its label points into `{name}_02`.

    A None `schema` triggers structural auto-detection of each level's columns.
    """
    table_in = f"{name}_01"
    columns = [row[0] for row in conn.execute(f'DESCRIBE "{table_in}"').fetchall()]
    if depth_column in columns:
        msg = f"depth_column {depth_column!r} already exists on {table_in!r}"
        raise ValueError(msg)

    level_columns: dict[int, LevelColumns] | None = None
    if schema is None:
        level_columns = detect_level_columns_or_single(conn, table_in)

    point_tables = []
    for n in levels:
        group_by, exclude = _level_group_by(schema, level_columns, n)
        if schema is None and group_by:
            verify_functional_cluster(conn, table_in, group_by[0], group_by)

        dissolved = f"{name}_02_tmp{n}"
        dissolve_stage.main(
            conn,
            table_in,
            dissolved,
            group_by=group_by,
            exclude=exclude,
            target_schema=schema,
        )
        _check_row_count(conn, dissolved, table_in, group_by)

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
