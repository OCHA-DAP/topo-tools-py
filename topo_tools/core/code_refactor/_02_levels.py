"""Resolves each level's own code column, structural or explicit."""

from duckdb import DuckDBPyConnection

from topo_tools.core.schema_map._level_columns import (
    detect_level_columns_or_single,
    verify_functional_cluster,
)
from topo_tools.core.schema_map._levels import detect_levels
from topo_tools.core.schema_map._target_schema import resolve_explicit_target_schema


def main(
    conn: DuckDBPyConnection,
    table: str,
    name_field: str | None,
    code_field: str | None,
) -> dict[int, str]:
    """Return {level: code_column}, structurally detected or explicit schema."""
    schema = resolve_explicit_target_schema(name_field, code_field)
    if schema is not None:
        levels = detect_levels(conn, table, schema)
        return {n: schema.code_field.format(n=n) for n in levels}

    level_columns = detect_level_columns_or_single(conn, table)
    # Relative depth, not admin0 convention: a truly constant coarsest
    # column is dropped before reaching here, so every level found is rankable.
    coded = [cols for _, cols in sorted(level_columns.items()) if cols.group_by]
    if not coded:
        msg = f"no admin hierarchy level detected in {table}"
        raise ValueError(msg)

    result: dict[int, str] = {}
    for n, cols in enumerate(coded, start=1):
        canonical = cols.group_by[0]
        verify_functional_cluster(conn, table, canonical, cols.group_by)
        result[n] = canonical
    return result
