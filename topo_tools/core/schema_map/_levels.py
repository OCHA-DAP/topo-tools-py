"""Derives admin hierarchy levels from a target schema + table."""

import re

from duckdb import DuckDBPyConnection

from topo_tools.core.admin_columns import field_prefix

from ._target_schema import TargetSchema


def level_prefix(schema: TargetSchema) -> str:
    """Return the literal prefix shared by every level's code column (e.g. "adm")."""
    return field_prefix(schema.code_field)


def detect_levels(
    conn: DuckDBPyConnection, table: str, schema: TargetSchema
) -> list[int]:
    """Return level 1..N present in table, plus level 0 if its own code column exists.

    Raises ValueError if a level in 1..N lacks its own code column, or none is found.
    """
    columns = {row[0] for row in conn.execute(f'DESCRIBE "{table}"').fetchall()}
    prefix = level_prefix(schema)
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)")
    found = sorted({int(m.group(1)) for c in columns if (m := pattern.match(c))})
    found = [n for n in found if n >= 1]
    if not found:
        msg = f"no {prefix!r}-prefixed level column found in {table}"
        raise ValueError(msg)

    max_level = found[-1]
    missing = [
        n
        for n in range(1, max_level + 1)
        if schema.code_field.format(n=n) not in columns
    ]
    if missing:
        cols = [schema.code_field.format(n=n) for n in missing]
        msg = f"missing code column(s) for level(s) {missing}: {cols}"
        raise ValueError(msg)

    levels = list(range(1, max_level + 1))
    if schema.code_field.format(n=0) in columns:
        levels.insert(0, 0)
    return levels
