"""Applies the safe fixes to every flagged name, in place in `{name}_01`."""

from duckdb import DuckDBPyConnection

from topo_tools.core.name_clean._constants import FIXED_KINDS


def _ident(column: str) -> str:
    return '"' + column.replace('"', '""') + '"'


def fixed_sql() -> str:
    """Return SQL true for a report row whose finding name-clean fixed."""
    kinds = ", ".join(f"'{k}'" for k in FIXED_KINDS)
    # A column row (no code) of an encoding kind may hold units with no repair.
    return (
        f"kind IN ({kinds}) AND (suggested IS NOT NULL "
        "OR (code_a IS NULL AND kind <> 'encoding-artifact'))"
    )


def main(conn: DuckDBPyConnection, name: str) -> None:
    """Rewrite each flagged unit's name as `name_clean(name)`, blanks untouched."""
    kinds = ", ".join(f"'{k}'" for k in FIXED_KINDS)
    targets = conn.execute(f"""--sql
        SELECT DISTINCT f.name_column, l.code_column
        FROM "{name}_03" f
        JOIN (SELECT DISTINCT level, name_column, code_column FROM "{name}_02") l
          USING (level, name_column)
        WHERE f.kind IN ({kinds}) AND f.suggested IS NOT NULL
    """).fetchall()
    for name_column, code_column in targets:
        col, code = _ident(name_column), _ident(code_column)
        conn.execute(
            f"""--sql
            UPDATE "{name}_01" SET {col} = name_clean({col})
            WHERE {code}::VARCHAR IN (
                SELECT code_a FROM "{name}_03"
                WHERE kind IN ({kinds}) AND suggested IS NOT NULL
                  AND name_column = ?
            )
              AND name_clean({col}) <> ''
        """,
            [name_column],
        )
