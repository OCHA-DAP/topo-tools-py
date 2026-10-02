"""Seeds a missing code column from its level's names, so it can be ranked."""

from duckdb import DuckDBPyConnection


def seed_code_from_names(
    conn: DuckDBPyConnection, table: str, level: int, code: str, name: str | None
) -> None:
    """Fill a VARCHAR code column with level's names; raise without a name column."""
    if name is None:
        msg = f"level {level} has neither {code!r} nor a name column in {table}"
        raise ValueError(msg)
    conn.execute(f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{code}" VARCHAR')
    conn.execute(f'UPDATE "{table}" SET "{code}" = "{name}"::VARCHAR')


def check_unique_names(
    conn: DuckDBPyConnection,
    table: str,
    level: int,
    name: str,
    parent: str | None = None,
) -> None:
    """Raise if two rows share a name under one parent, so seeding would merge them."""
    keys = ", ".join(f'"{c}"::VARCHAR' for c in (parent, name) if c is not None)
    repeats = conn.execute(f"""--sql
        SELECT concat_ws(' > ', {keys}) FROM "{table}"
        WHERE "{name}" IS NOT NULL
        GROUP BY ALL HAVING COUNT(*) > 1 ORDER BY 1
    """).fetchall()
    if repeats:
        examples = ", ".join(repr(r[0]) for r in repeats[:5])
        msg = (
            f"level {level}: {len(repeats)} name(s) repeat under one parent in "
            f"{table} ({examples}); codes seeded from names would merge them, so "
            "tell them apart or add a code column"
        )
        raise ValueError(msg)
