"""Top-down per-level code assignment: level 0 literal, 1..N via the shared cascade."""

from duckdb import DuckDBPyConnection

from topo_tools.core.admin_columns import next_free_sibling
from topo_tools.core.code import CodeFormat, assign_new_codes
from topo_tools.core.code_refactor._02_levels import Level
from topo_tools.core.code_refactor._constants import SOURCE_CODES


def _copy_source_codes(
    conn: DuckDBPyConnection, table: str, levels: dict[int, Level]
) -> None:
    """Keep each level's source code in its next free numbered sibling column."""
    columns = [r[0] for r in conn.execute(f'DESCRIBE "{table}"').fetchall()]
    taken = set(columns)
    siblings: dict[str, str] = {}
    for n in sorted(levels):
        level = levels[n]
        if n == 0 or level.seeded:
            continue
        siblings[level.code] = next_free_sibling(level.code, taken)
        taken.add(siblings[level.code])
    select = []
    for column in columns:
        select.append(f'"{column}"')
        if column in siblings:
            select.append(f'"{column}"::VARCHAR AS "{siblings[column]}"')
    conn.execute(
        f'CREATE OR REPLACE TABLE "{table}" AS '
        f'SELECT {", ".join(select)} FROM "{table}"'
    )


def _seed_from_names(
    conn: DuckDBPyConnection, table: str, levels: dict[int, Level]
) -> None:
    """Give a level with no code column one holding its own names, to rank on."""
    for n, level in sorted(levels.items()):
        if not level.seeded:
            continue
        if level.name is None:
            msg = f"level {n} has neither {level.code!r} nor a name column in {table}"
            raise ValueError(msg)
        conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{level.code}" VARCHAR')
        conn.execute(f'UPDATE "{table}" SET "{level.code}" = "{level.name}"::VARCHAR')


def _check_embeddable(
    conn: DuckDBPyConnection, table: str, n: int, level: Level, fmt: CodeFormat
) -> None:
    """Raise unless every row has a source code, all one length without a delimiter."""
    nulls, lengths = conn.execute(f"""--sql
        SELECT COUNT(*) FILTER (WHERE "{level.code}" IS NULL),
               list(DISTINCT length("{level.code}"::VARCHAR)) FILTER (
                   WHERE "{level.code}" IS NOT NULL
               )
        FROM "{table}"
    """).fetchone()
    if nulls:
        msg = f"level {n} ({level.code!r}) has {nulls} row(s) with no source code"
        raise ValueError(msg)
    if fmt.delimiter == "" and len(lengths or []) > 1:
        msg = (
            f"level {n} ({level.code!r}) source codes vary in length "
            f"{sorted(lengths)}; without a delimiter the code can't be split"
        )
        raise ValueError(msg)


def main(
    conn: DuckDBPyConnection,
    table: str,
    *,
    levels: dict[int, Level],
    fmt: CodeFormat,
    source_codes: str = "replace",
) -> None:
    """Assign a code into each level's own column, in place, root to leaf."""
    if source_codes not in SOURCE_CODES:
        msg = f"source_codes must be one of {SOURCE_CODES}, got {source_codes!r}"
        raise ValueError(msg)
    fmt.check_level_count(sum(1 for n in levels if n >= 1))
    if source_codes == "copy":
        _copy_source_codes(conn, table, levels)
    _seed_from_names(conn, table, levels)
    if 0 in levels:
        conn.execute(f'UPDATE "{table}" SET "{levels[0].code}" = ?', [fmt.root_code])

    parent_sql = f"'{fmt.root_code}'"
    parent_column: str | None = None
    for n in sorted(level for level in levels if level >= 1):
        code_column = levels[n].code
        if source_codes == "embed" and not levels[n].seeded:
            _check_embeddable(conn, table, n, levels[n], fmt)
            conn.execute(
                f'UPDATE "{table}" SET "{code_column}" = '
                f'{parent_sql} || ? || "{code_column}"::VARCHAR',
                [fmt.delimiter],
            )
            parent_sql = f'"{code_column}"'
            parent_column = code_column
            continue
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
            level=n,
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
