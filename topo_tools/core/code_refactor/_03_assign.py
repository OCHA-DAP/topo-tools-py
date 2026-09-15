"""Top-down per-level code assignment: level 0 literal, 1..N via the shared cascade."""

from duckdb import DuckDBPyConnection

from topo_tools.core.code import CodeFormat, assign_new_codes


def main(
    conn: DuckDBPyConnection,
    table: str,
    *,
    levels: dict[int, str],
    fmt: CodeFormat,
) -> None:
    """Assign a fresh code into each level's own column, in place, root to leaf."""
    if 0 in levels:
        conn.execute(f'UPDATE "{table}" SET "{levels[0]}" = ?', [fmt.root_code])

    parent_sql = f"'{fmt.root_code}'"
    for n in sorted(level for level in levels if level >= 1):
        code_column = levels[n]
        staging = f"{table}_code_lvl{n}"
        conn.execute(f"""--sql
            CREATE OR REPLACE TEMP TABLE "{staging}" AS
            SELECT DISTINCT
                "{code_column}" AS orig_code,
                "{code_column}" AS code_val,
                {parent_sql} AS parent_code
            FROM "{table}"
        """)
        assign_new_codes(
            conn,
            staging,
            id_column="orig_code",
            parent_column="parent_code",
            sort_columns=["code_val"],
            code_column="code_val",
            fmt=fmt,
        )
        conn.execute(f"""--sql
            UPDATE "{table}" t
            SET "{code_column}" = s.code_val
            FROM "{staging}" s
            WHERE t."{code_column}" = s.orig_code
        """)
        conn.execute(f'DROP TABLE IF EXISTS "{staging}"')
        parent_sql = f'"{code_column}"'
