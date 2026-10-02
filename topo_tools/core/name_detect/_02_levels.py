"""Resolves each level's code and name columns, then lists every unit's names."""

from dataclasses import dataclass

from duckdb import DuckDBPyConnection

from topo_tools.core.admin_columns import sibling_name
from topo_tools.core.schema_map._level_columns import (
    detect_level_columns_or_single,
    supplemental_columns,
)
from topo_tools.core.schema_map._levels import detect_levels
from topo_tools.core.schema_map._target_schema import resolve_explicit_target_schema


@dataclass(frozen=True)
class Level:
    """One level's code column and its name columns, primary first (may be none)."""

    code: str
    names: tuple[str, ...]


def _with_siblings(name: str, columns: set[str]) -> tuple[str, ...]:
    """Return name plus its numbered siblings present in columns (adm2_name1, ...)."""
    found = [name]
    index = 1
    while (sibling := sibling_name(name, index)) in columns:
        found.append(sibling)
        index += 1
    return tuple(found)


def resolve_levels(
    conn: DuckDBPyConnection,
    table: str,
    name_field: str | None,
    code_field: str | None,
) -> dict[int, Level]:
    """Return {level: Level} for every coded level, names or not."""
    columns = {r[0] for r in conn.execute(f'DESCRIBE "{table}"').fetchall()}
    schema = resolve_explicit_target_schema(name_field, code_field)
    result: dict[int, Level] = {}
    if schema is not None:
        for n in detect_levels(conn, table, schema, require_codes=False):
            code, name = schema.code_field.format(n=n), schema.name_field.format(n=n)
            # Level 0 is only a parent (one file may hold several countries).
            names = _with_siblings(name, columns) if n and name in columns else ()
            if code not in columns:
                if names:
                    msg = f"level {n} has names ({name!r}) but no code column {code!r}"
                    raise ValueError(msg)
                continue
            result[n] = Level(code, names)
    else:
        detected = detect_level_columns_or_single(conn, table)
        coded = [(n, cols) for n, cols in sorted(detected.items()) if cols.group_by]
        # A skipped level would compare names under the wrong parent, so never guess.
        found = [n for n, _ in coded]
        skipped = not found or found != list(range(found[0], found[-1] + 1))
        if skipped or supplemental_columns(conn, table):
            msg = (
                f"{table}: admin levels could not be detected reliably; "
                "pass --name-field/--code-field explicitly"
            )
            raise ValueError(msg)
        for n, (_, cols) in enumerate(coded, start=1):
            name = (
                cols.name_column if cols.name_column in cols.identity_columns else None
            )
            result[n] = Level(
                cols.group_by[0], _with_siblings(name, columns) if name else ()
            )
    if not any(level.names for level in result.values()):
        msg = f"no admin level with both a code and a name column found in {table}"
        raise ValueError(msg)
    return result


def _ident(column: str) -> str:
    return '"' + column.replace('"', '""') + '"'


def _literal(column: str) -> str:
    return "'" + column.replace("'", "''") + "'"


def main(
    conn: DuckDBPyConnection,
    name: str,
    *,
    name_field: str | None = None,
    code_field: str | None = None,
) -> None:
    """Write `{name}_02`: one row per level, name column, unit code and name."""
    table = f"{name}_01"
    levels = resolve_levels(conn, table, name_field, code_field)
    selects = []
    for n, level in sorted(levels.items()):
        parent = levels.get(n - 1)
        parent_sql = f"{_ident(parent.code)}::VARCHAR" if parent else "NULL::VARCHAR"
        for index, column in enumerate(level.names):  # empty for a nameless level
            selects.append(f"""--sql
                SELECT {n} AS level, {_literal(column)} AS name_column,
                       {index} AS name_index, {_literal(level.code)} AS code_column,
                       {_ident(level.code)}::VARCHAR AS code,
                       {parent_sql} AS parent_code,
                       {_ident(column)}::VARCHAR AS name, COUNT(*) AS row_count
                FROM "{table}"
                GROUP BY ALL
            """)
    conn.execute(
        f'CREATE OR REPLACE TABLE "{name}_02" AS {" UNION ALL ".join(selects)}'
    )
