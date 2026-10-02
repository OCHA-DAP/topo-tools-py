"""Resolves each side's own per-level code column; detects OLD's own CodeFormat."""

from dataclasses import dataclass

from duckdb import DuckDBPyConnection

from topo_tools.core.code import (
    CodeFormat,
    check_unique_names,
    detect_code_format,
    detect_undelimited_format,
    has_delimiter,
    parse_min_width,
    seed_code_from_names,
)
from topo_tools.core.schema_map._level_columns import (
    LevelColumns,
    detect_level_columns_or_single,
    supplemental_columns,
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
    *,
    seed_missing_codes: bool = False,
) -> SideLevels:
    """Resolve one side's per-level code/name columns, structural or explicit."""
    schema = resolve_explicit_target_schema(name_field, code_field)
    if schema is not None:
        # Level 0 is the root itself, never recoded.
        levels = [
            n
            for n in detect_levels(
                conn, table, schema, require_codes=not seed_missing_codes
            )
            if n >= 1
        ]
        columns = {n: schema.code_field.format(n=n) for n in levels}
        names = {n: schema.name_field.format(n=n) for n in levels}
        present = {r[0] for r in conn.execute(f'DESCRIBE "{table}"').fetchall()}
        for n in levels:
            if columns[n] not in present:
                name = names[n] if names[n] in present else None
                seed_code_from_names(conn, table, n, columns[n], name)
                if n - 1 in columns:
                    # Same-named units under different parents must stay apart.
                    conn.execute(
                        f'UPDATE "{table}" SET "{columns[n]}" = '
                        f'"{columns[n - 1]}"::VARCHAR || \' > \' || "{columns[n]}"'
                    )
                if n == max(levels):
                    check_unique_names(conn, table, n, columns[n])
        return SideLevels(
            columns=columns, names=names, schema=schema, level_columns=None
        )

    raw = detect_level_columns_or_single(conn, table)
    coded = [(n, cols) for n, cols in sorted(raw.items()) if cols.group_by]
    if not coded:
        msg = f"no admin hierarchy level detected in {table}"
        raise ValueError(msg)
    # A skipped level would corrupt every code below it, so never guess.
    if supplemental := supplemental_columns(conn, table):
        msg = (
            f"{table}: {supplemental} group units like a level but were not "
            "detected as one; pass --code-field-a/--name-field-a or "
            "--code-field-b/--name-field-b explicitly"
        )
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
    parent: str | None = None
    for n, (_, cols) in enumerate(coded, start=1):
        canonical = cols.group_by[0]
        verify_functional_cluster(
            conn, table, canonical, cols.group_by, parent_column=parent
        )
        columns[n] = canonical
        parent = canonical
        names[n] = cols.name_column
        level_columns[n] = cols
    return SideLevels(
        columns=columns, names=names, schema=None, level_columns=level_columns
    )


def _check_codes_and_names(
    conn: DuckDBPyConnection, table: str, side: SideLevels
) -> None:
    """Raise on a missing code, or a code with more than one name, at any level."""
    present = {r[0] for r in conn.execute(f'DESCRIBE "{table}"').fetchall()}
    for n, code in sorted(side.columns.items()):
        (missing,) = conn.execute(f"""--sql
            SELECT COUNT(*) FROM "{table}"
            WHERE "{code}" IS NULL OR trim("{code}"::VARCHAR) = ''
        """).fetchone()
        if missing:
            msg = f"level {n} ({code!r}) has {missing} row(s) with no code in {table}"
            raise ValueError(msg)
        name = side.names[n]
        if name is None or name not in present:
            continue
        (mixed,) = conn.execute(f"""--sql
            SELECT COUNT(*) FROM (
                SELECT "{code}" FROM "{table}" GROUP BY 1
                HAVING COUNT(DISTINCT "{name}") > 1
            )
        """).fetchone()
        if mixed:
            msg = (
                f"level {n}: {mixed} {code!r} value(s) in {table} have more than "
                f"one {name!r} value"
            )
            raise ValueError(msg)


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
    min_width: int | str | None,
) -> tuple[SideLevels, SideLevels, CodeFormat]:
    """Resolve OLD/NEW per-level columns; detect (or accept an override for) fmt."""
    side_a = _resolve_side(conn, old_table, name_field_a, code_field_a)
    side_b = _resolve_side(
        conn, new_table, name_field_b, code_field_b, seed_missing_codes=True
    )

    if sorted(side_a.columns) != sorted(side_b.columns):
        msg = (
            f"level mismatch between old ({sorted(side_a.columns)}) and new "
            f"({sorted(side_b.columns)}); a real level-count change needs a "
            "human decision, not an automatic pass"
        )
        raise ValueError(msg)
    _check_codes_and_names(conn, old_table, side_a)
    _check_codes_and_names(conn, new_table, side_b)

    if root_code is None or delimiter is None or min_width is None:
        finest = max(side_a.columns)
        if delimiter == "" or (
            delimiter is None
            and not has_delimiter(conn, old_table, side_a.columns[finest])
        ):
            detected = detect_undelimited_format(conn, old_table, side_a.columns)
        else:
            detected = detect_code_format(conn, old_table, side_a.columns[finest])
    fmt = CodeFormat(
        root_code=root_code if root_code is not None else detected.root_code,
        delimiter=delimiter if delimiter is not None else detected.delimiter,
        min_width=(
            parse_min_width(min_width) if min_width is not None else detected.min_width
        ),
    )
    if fmt.delimiter == "" and fmt.min_width == "auto":
        msg = "min_width auto needs a delimiter; without one, widths must match OLD's"
        raise ValueError(msg)
    fmt.check_level_count(len(side_a.columns))
    return side_a, side_b, fmt
