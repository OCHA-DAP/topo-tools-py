"""Copies the matched parent's hierarchy columns onto each child, geometry untouched."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from topo_tools.core.admin_columns import (
    canonical_order,
    sibling_name,
    template_families,
)
from topo_tools.core.duckdb_utils import quote_identifier
from topo_tools.core.schema_map._level_columns import detect_level_columns
from topo_tools.core.schema_map._levels import detect_levels
from topo_tools.core.schema_map._target_schema import (
    DEFAULT_TARGET_SCHEMA,
    TargetSchema,
)

logger = getLogger(__name__)


def _column_types(conn: DuckDBPyConnection, table: str) -> dict[str, str]:
    rows = conn.execute(f"DESCRIBE {quote_identifier(table)}").fetchall()
    return {r[0]: r[1] for r in rows}


def _columns(conn: DuckDBPyConnection, table: str) -> list[str]:
    return list(_column_types(conn, table))


def parent_hierarchy_columns(
    conn: DuckDBPyConnection, table: str, schema: TargetSchema | None
) -> list[str]:
    """Every admin-hierarchy column in table, in its own column order."""
    columns = _columns(conn, table)
    if schema is not None:
        levels = detect_levels(conn, table, schema)
        families = template_families(
            columns, levels, schema.name_field, schema.code_field
        )
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
    while sibling_name(column, n) in taken:
        n += 1
    return sibling_name(column, n)


def main(conn: DuckDBPyConnection, name: str, schema: TargetSchema | None) -> None:
    """Build `{name}_03` (joined output) and `{name}_03_mismatch` (differing values)."""
    parent_table = f"{name}_parent_01"
    child_types = _column_types(conn, f"{name}_child_01")
    parent_types = _column_types(conn, parent_table)
    child_columns = list(child_types)
    taken = set(child_columns) | set(parent_types)

    exprs = {
        c: f"c.{quote_identifier(c)}"
        for c in child_columns
        if c not in {"fid", "geom", "source_file"}
    }
    mismatch_parts = []
    for column in parent_hierarchy_columns(conn, parent_table, schema):
        col = quote_identifier(column)
        if column not in child_columns:
            exprs[column] = f"p.{col}"
            continue
        # Mismatched types compare as text so an unrelated cast can't fail.
        cast = "" if child_types[column] == parent_types[column] else "::VARCHAR"
        distinct = f"c.{col}{cast} IS DISTINCT FROM p.{col}{cast}"
        differs = conn.execute(f"""--sql
            SELECT COUNT(*) FROM "{name}_child_01" c
            JOIN "{name}_02_assign" a ON a.child_fid = c.fid
            JOIN "{parent_table}" p ON p.fid = a.parent_fid
            WHERE {distinct}
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
        exprs[sibling] = f"p.{col}"
        mismatch_parts.append(f"""
            SELECT c.fid AS child_fid, a.parent_fid, '{column.replace("'", "''")}'
                       AS column_name,
                   c.{col}::VARCHAR AS child_value, p.{col}::VARCHAR AS parent_value
            FROM "{name}_child_01" c
            JOIN "{name}_02_assign" a ON a.child_fid = c.fid
            JOIN "{parent_table}" p ON p.fid = a.parent_fid
            WHERE c.{col} IS NOT NULL AND p.{col} IS NOT NULL
              AND {distinct}
        """)

    template = schema or DEFAULT_TARGET_SCHEMA
    columns, sort_column = canonical_order(
        list(exprs), template.name_field, template.code_field
    )
    if sort_column is None:
        logger.warning(
            "schema-join: no %r column found; rows keep input order "
            "(pass --name-field/--code-field for another schema)",
            template.code_field,
        )
    select = "".join(f", {exprs[c]} AS {quote_identifier(c)}" for c in columns)
    order = f"{exprs[sort_column]} NULLS LAST, " if sort_column else ""
    # out_fid is the output row number, so issue rows point at output rows.
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_03" AS
        SELECT c.fid, row_number() OVER (ORDER BY {order}c.fid) AS out_fid,
               c.geom{select}, c.source_file
        FROM "{name}_child_01" c
        LEFT JOIN "{name}_02_assign" a ON a.child_fid = c.fid
        LEFT JOIN "{parent_table}" p ON p.fid = a.parent_fid
        ORDER BY out_fid
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
