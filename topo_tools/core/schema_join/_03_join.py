"""Copies the matched parent's hierarchy columns onto each child, geometry untouched."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from topo_tools.core.duckdb_utils import quote_identifier
from topo_tools.core.schema_map._level_columns import detect_level_columns
from topo_tools.core.schema_map._levels import (
    column_families,
    detect_levels,
    level_prefix,
)
from topo_tools.core.schema_map._target_schema import TargetSchema

logger = getLogger(__name__)


def _columns(conn: DuckDBPyConnection, table: str) -> list[str]:
    return [
        r[0] for r in conn.execute(f"DESCRIBE {quote_identifier(table)}").fetchall()
    ]


def parent_hierarchy_columns(
    conn: DuckDBPyConnection, table: str, schema: TargetSchema | None
) -> list[str]:
    """Every admin-hierarchy column in table, in its own column order."""
    columns = _columns(conn, table)
    if schema is not None:
        levels = detect_levels(conn, table, schema)
        families = column_families(columns, levels, level_prefix(schema))
        selected = {c for family in families.values() for c in family.values()}
    else:
        selected = {
            c
            for level in detect_level_columns(conn, table).values()
            for c in level.identity_columns
        }
    return [c for c in columns if c in selected]


def _next_free_name(column: str, taken: set[str]) -> str:
    n = 1
    while f"{column}{n}" in taken:
        n += 1
    return f"{column}{n}"


def main(conn: DuckDBPyConnection, name: str, schema: TargetSchema | None) -> None:
    """Build `{name}_03` (joined output) and `{name}_03_mismatch` (differing values)."""
    parent_table = f"{name}_parent_01"
    child_columns = _columns(conn, f"{name}_child_01")
    taken = set(child_columns) | set(_columns(conn, parent_table))

    select_parts = []
    mismatch_parts = []
    for column in parent_hierarchy_columns(conn, parent_table, schema):
        col = quote_identifier(column)
        if column not in child_columns:
            select_parts.append(f"p.{col} AS {col}")
            continue
        differs = conn.execute(f"""--sql
            SELECT COUNT(*) FROM "{name}_child_01" c
            JOIN "{name}_02_assign" a ON a.child_fid = c.fid
            JOIN "{parent_table}" p ON p.fid = a.parent_fid
            WHERE c.{col} IS DISTINCT FROM p.{col}
        """).fetchone()[0]
        if not differs:
            continue
        sibling = _next_free_name(column, taken)
        taken.add(sibling)
        logger.warning(
            "schema-join: %d child row(s) differ from the parent on %r; "
            "adding the parent's values as %r",
            differs,
            column,
            sibling,
        )
        select_parts.append(f"p.{col} AS {quote_identifier(sibling)}")
        mismatch_parts.append(f"""
            SELECT c.fid AS child_fid, a.parent_fid, '{column.replace("'", "''")}'
                       AS column_name,
                   c.{col}::VARCHAR AS child_value, p.{col}::VARCHAR AS parent_value
            FROM "{name}_child_01" c
            JOIN "{name}_02_assign" a ON a.child_fid = c.fid
            JOIN "{parent_table}" p ON p.fid = a.parent_fid
            WHERE c.{col} IS NOT NULL AND p.{col} IS NOT NULL
              AND c.{col} IS DISTINCT FROM p.{col}
        """)

    extra = "".join(f", {part}" for part in select_parts)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_03" AS
        SELECT c.* EXCLUDE (geom){extra}, c.geom
        FROM "{name}_child_01" c
        LEFT JOIN "{name}_02_assign" a ON a.child_fid = c.fid
        LEFT JOIN "{parent_table}" p ON p.fid = a.parent_fid
        ORDER BY c.fid
    """)
    empty = (
        "SELECT NULL::BIGINT AS child_fid, NULL::BIGINT AS parent_fid, "
        "NULL::VARCHAR AS column_name, NULL::VARCHAR AS child_value, "
        "NULL::VARCHAR AS parent_value WHERE FALSE"
    )
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_03_mismatch" AS
        {" UNION ALL ".join(mismatch_parts) if mismatch_parts else empty}
    """)
