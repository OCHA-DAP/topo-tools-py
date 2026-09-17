"""Resolves each side's own per-level code column; detects OLD's own CodeFormat."""

from dataclasses import dataclass

from duckdb import DuckDBPyConnection

from topo_tools.core.code import CodeFormat, detect_code_format
from topo_tools.core.schema_map._level_columns import (
    LevelColumns,
    detect_level_columns_or_single,
    verify_functional_cluster,
)
from topo_tools.core.schema_map._levels import detect_levels
from topo_tools.core.schema_map._target_schema import (
    TargetSchema,
    resolve_explicit_target_schema,
)


@dataclass(frozen=True)
class SideLevels:
    """One side's (OLD or NEW) resolved per-level code/name columns, renumbered 1..N."""

    columns: dict[int, str]
    names: dict[int, str | None]
    schema: TargetSchema | None
    level_columns: dict[int, LevelColumns] | None


def _resolve_side(
    conn: DuckDBPyConnection,
    table: str,
    name_field: str | None,
    code_field: str | None,
) -> SideLevels:
    """Resolve one side's per-level code/name columns, structural or explicit."""
    schema = resolve_explicit_target_schema(name_field, code_field)
    if schema is not None:
        levels = detect_levels(conn, table, schema)
        columns = {n: schema.code_field.format(n=n) for n in levels}
        names = {n: schema.name_field.format(n=n) for n in levels}
        return SideLevels(
            columns=columns, names=names, schema=schema, level_columns=None
        )

    raw = detect_level_columns_or_single(conn, table)
    coded = [(n, cols) for n, cols in sorted(raw.items()) if cols.group_by]
    if not coded:
        msg = f"no admin hierarchy level detected in {table}"
        raise ValueError(msg)
    missing = [n for n, cols in coded if not cols.has_code]
    if missing:
        msg = (
            f"no existing code column to overwrite for level(s) {missing} in "
            f"{table}; pass --code-field-a/--name-field-a or --code-field-b/"
            "--name-field-b explicitly"
        )
        raise ValueError(msg)

    columns: dict[int, str] = {}
    names: dict[int, str | None] = {}
    level_columns: dict[int, LevelColumns] = {}
    for n, (_, cols) in enumerate(coded, start=1):
        canonical = cols.group_by[0]
        verify_functional_cluster(conn, table, canonical, cols.group_by)
        columns[n] = canonical
        names[n] = cols.name_column
        level_columns[n] = cols
    return SideLevels(
        columns=columns, names=names, schema=None, level_columns=level_columns
    )


def main(  # noqa: PLR0913
    conn: DuckDBPyConnection,
    old_table: str,
    new_table: str,
    *,
    name_field_a: str | None,
    code_field_a: str | None,
    name_field_b: str | None,
    code_field_b: str | None,
    root_code: str | None,
    delimiter: str | None,
    min_width: int | None,
) -> tuple[SideLevels, SideLevels, CodeFormat]:
    """Resolve OLD/NEW per-level columns; detect (or accept an override for) fmt."""
    side_a = _resolve_side(conn, old_table, name_field_a, code_field_a)
    side_b = _resolve_side(conn, new_table, name_field_b, code_field_b)

    if sorted(side_a.columns) != sorted(side_b.columns):
        msg = (
            f"level mismatch between old ({sorted(side_a.columns)}) and new "
            f"({sorted(side_b.columns)}); a real level-count change needs a "
            "human decision, not an automatic pass"
        )
        raise ValueError(msg)

    if root_code is None or delimiter is None or min_width is None:
        finest = max(side_a.columns)
        detected = detect_code_format(conn, old_table, side_a.columns[finest])
    fmt = CodeFormat(
        root_code=root_code if root_code is not None else detected.root_code,
        delimiter=delimiter if delimiter is not None else detected.delimiter,
        min_width=min_width if min_width is not None else detected.min_width,
    )
    return side_a, side_b, fmt
