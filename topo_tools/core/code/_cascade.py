"""Ranks rows per parent group, assigns sequential formatted hierarchical codes."""

from duckdb import DuckDBPyConnection

from topo_tools.core.code._code_format import CodeFormat
from topo_tools.core.code._next_available import next_available_integer


def _sql_literal(value: str) -> str:
    """Single-quote a SQL string literal, escaping any embedded quote."""
    return "'" + value.replace("'", "''") + "'"


def assign_new_codes(  # noqa: PLR0913
    conn: DuckDBPyConnection,
    table: str,
    *,
    id_column: str,
    parent_column: str,
    sort_columns: list[str],
    code_column: str,
    fmt: CodeFormat,
    existing_codes: list[str] | None = None,
) -> None:
    """Assign each row in table a new sequential code within its own parent group."""
    existing_codes = existing_codes or []
    parents = [
        row[0]
        for row in conn.execute(
            f'SELECT DISTINCT "{parent_column}" FROM "{table}"'
        ).fetchall()
    ]
    base_by_parent = {
        parent: next_available_integer(existing_codes, parent, fmt)
        for parent in parents
    }

    base_table = f"{table}_code_base"
    conn.execute(f"""--sql
        CREATE OR REPLACE TEMP TABLE "{base_table}" (
            parent_code VARCHAR, base_n INTEGER
        )
    """)
    conn.executemany(
        f'INSERT INTO "{base_table}" VALUES (?, ?)', list(base_by_parent.items())
    )

    order_sql = ", ".join(f'"{c}" NULLS LAST' for c in sort_columns)
    ranked_table = f"{table}_code_ranked"
    # lpad truncates a too-long string (unlike Python's zfill); widen the
    # target width to the tail's own length first so it only ever pads.
    conn.execute(f"""--sql
        CREATE OR REPLACE TEMP TABLE "{ranked_table}" AS
        WITH numbered AS (
            SELECT
                src."{id_column}" AS id_value,
                src."{parent_column}" AS parent_code,
                CAST(
                    base.base_n - 1 + ROW_NUMBER() OVER (
                        PARTITION BY src."{parent_column}" ORDER BY {order_sql}
                    ) AS VARCHAR
                ) AS tail
            FROM "{table}" src
            JOIN "{base_table}" base ON base.parent_code = src."{parent_column}"
        )
        SELECT
            id_value,
            parent_code || {_sql_literal(fmt.delimiter)} ||
            lpad(tail, CAST(GREATEST({fmt.min_width}, LENGTH(tail)) AS INTEGER), '0')
            AS new_code
        FROM numbered
    """)
    conn.execute(f"""--sql
        UPDATE "{table}" t
        SET "{code_column}" = r.new_code
        FROM "{ranked_table}" r
        WHERE t."{id_column}" = r.id_value
    """)
    conn.execute(f'DROP TABLE IF EXISTS "{base_table}"')
    conn.execute(f'DROP TABLE IF EXISTS "{ranked_table}"')
