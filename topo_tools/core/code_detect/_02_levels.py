"""Resolves each level's code and name columns, then lists every unit's codes."""

from duckdb import DuckDBPyConnection

from topo_tools.core.duckdb_utils import quote_identifier
from topo_tools.core.schema_map._resolve_levels import resolve_levels


def _literal(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def main(
    conn: DuckDBPyConnection,
    name: str,
    *,
    name_field: str | None = None,
    code_field: str | None = None,
) -> None:
    """Write `{name}_02`: one row per level, name column, unit code and name."""
    table = f"{name}_01"
    levels = resolve_levels(conn, table, name_field, code_field)
    selects = []
    for n, level in sorted(levels.items()):
        parent = levels.get(n - 1)
        parent_sql = (
            f"{quote_identifier(parent.code)}::VARCHAR" if parent else "NULL::VARCHAR"
        )
        # A nameless level still lists its codes, under a NULL name column.
        for index, column in enumerate(level.names or (None,)):
            name_sql = f"{quote_identifier(column)}::VARCHAR" if column else "NULL"
            selects.append(f"""--sql
                SELECT {n} AS level,
                       {_literal(column) if column else "NULL"} AS name_column,
                       {index} AS name_index,
                       {_literal(level.code)} AS code_column,
                       {quote_identifier(level.code)}::VARCHAR AS code,
                       {parent_sql} AS parent_code,
                       {name_sql}::VARCHAR AS name, COUNT(*) AS row_count
                FROM "{table}"
                GROUP BY ALL
            """)
    conn.execute(
        f'CREATE OR REPLACE TABLE "{name}_02" AS {" UNION ALL ".join(selects)}'
    )
