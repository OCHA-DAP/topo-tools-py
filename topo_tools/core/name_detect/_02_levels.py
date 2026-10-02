"""Resolves each level's code and name columns, then lists every unit's names."""

from duckdb import DuckDBPyConnection

from topo_tools.core.schema_map._resolve_levels import resolve_levels


def _ident(column: str) -> str:
    return '"' + column.replace('"', '""') + '"'


def _literal(column: str) -> str:
    return "'" + column.replace("'", "''") + "'"


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
        parent_sql = f"{_ident(parent.code)}::VARCHAR" if parent else "NULL::VARCHAR"
        for index, column in enumerate(level.names):  # empty for a nameless level
            selects.append(f"""--sql
                SELECT {n} AS level, {_literal(column)} AS name_column,
                       {index} AS name_index, {_literal(level.code)} AS code_column,
                       {_ident(level.code)}::VARCHAR AS code,
                       {parent_sql} AS parent_code,
                       {_ident(column)}::VARCHAR AS name, COUNT(*) AS row_count
                FROM "{table}"
                GROUP BY ALL
            """)
    conn.execute(
        f'CREATE OR REPLACE TABLE "{name}_02" AS {" UNION ALL ".join(selects)}'
    )
