"""Resolves each level's own code column, structural or explicit."""

from dataclasses import dataclass

from duckdb import DuckDBPyConnection

from topo_tools.core.schema_map._level_columns import (
    detect_level_columns_or_single,
    supplemental_columns,
    verify_functional_cluster,
)
from topo_tools.core.schema_map._levels import detect_levels
from topo_tools.core.schema_map._target_schema import resolve_explicit_target_schema


@dataclass(frozen=True)
class Level:
    """One level's code column, name column, and whether the input lacks the code."""

    code: str
    name: str | None = None
    seeded: bool = False


def main(
    conn: DuckDBPyConnection,
    table: str,
    name_field: str | None,
    code_field: str | None,
) -> dict[int, Level]:
    """Return {level: Level}, structurally detected or explicit schema."""
    schema = resolve_explicit_target_schema(name_field, code_field)
    if schema is not None:
        columns = {r[0] for r in conn.execute(f'DESCRIBE "{table}"').fetchall()}
        levels = detect_levels(conn, table, schema, require_codes=False)
        result = {}
        for n in levels:
            code, name = schema.code_field.format(n=n), schema.name_field.format(n=n)
            result[n] = Level(
                code, name if name in columns else None, code not in columns
            )
        return result

    level_columns = detect_level_columns_or_single(conn, table)
    # Relative depth, not admin0 convention: a truly constant coarsest
    # column is dropped before reaching here, so every level found is rankable.
    coded = [(n, cols) for n, cols in sorted(level_columns.items()) if cols.group_by]
    if not coded:
        msg = f"no admin hierarchy level detected in {table}"
        raise ValueError(msg)
    # A skipped level would corrupt every code below it, so never guess.
    if supplemental := supplemental_columns(conn, table):
        msg = (
            f"{table}: {supplemental} group units like a level but were not "
            "detected as one; pass --code-field/--name-field explicitly"
        )
        raise ValueError(msg)
    missing = [n for n, cols in coded if not cols.has_code]
    if missing:
        msg = (
            f"no existing code column to overwrite for level(s) {missing} in "
            f"{table}; pass --code-field/--name-field explicitly"
        )
        raise ValueError(msg)

    result: dict[int, Level] = {}
    parent: str | None = None
    for n, (_, cols) in enumerate(coded, start=1):
        canonical = cols.group_by[0]
        verify_functional_cluster(
            conn, table, canonical, cols.group_by, parent_column=parent
        )
        result[n] = Level(canonical, cols.name_column)
        parent = canonical
    return result
