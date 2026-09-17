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
    parent_column: str | None = None
    for n in sorted(level for level in levels if level >= 1):
        code_column = levels[n]
        staging = f"{table}_code_lvl{n}"
        conn.execute(f"""--sql
            CREATE OR REPLACE TEMP TABLE "{staging}" AS
            SELECT ROW_NUMBER() OVER () AS row_id, orig_code,
                   orig_code AS code_val, parent_code
            FROM (
                SELECT DISTINCT
                    "{code_column}" AS orig_code,
                    {parent_sql} AS parent_code
                FROM "{table}"
            ) d
        """)
        assign_new_codes(
            conn,
            staging,
            id_column="row_id",
            parent_column="parent_code",
            sort_columns=["code_val"],
            code_column="code_val",
            fmt=fmt,
        )
        # A raw value MAY repeat across parents; match on parent too so this
        # never collides with, or drops, the same value/NULL elsewhere.
        parent_match = (
            "TRUE"
            if parent_column is None
            else f't."{parent_column}" IS NOT DISTINCT FROM s.parent_code'
        )
        conn.execute(f"""--sql
            UPDATE "{table}" t
            SET "{code_column}" = s.code_val
            FROM "{staging}" s
            WHERE t."{code_column}" IS NOT DISTINCT FROM s.orig_code AND {parent_match}
        """)
        conn.execute(f'DROP TABLE IF EXISTS "{staging}"')
        parent_sql = f'"{code_column}"'
        parent_column = code_column
