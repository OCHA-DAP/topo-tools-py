"""Seeds a missing code column from its level's names, so it can be ranked."""

from duckdb import DuckDBPyConnection


def seed_code_from_names(
    conn: DuckDBPyConnection, table: str, level: int, code: str, name: str | None
) -> None:
    """Add code column holding level's own names; raise if there's no name column."""
    if name is None:
        msg = f"level {level} has neither {code!r} nor a name column in {table}"
        raise ValueError(msg)
    conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{code}" VARCHAR')
    conn.execute(f'UPDATE "{table}" SET "{code}" = "{name}"::VARCHAR')
