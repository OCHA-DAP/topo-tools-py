"""Fills NULL adm{n}<suffix> columns down and stamps each row's real depth."""

from duckdb import DuckDBPyConnection

from topo_tools.core.admin_columns import column_families, field_prefix
from topo_tools.core.schema_map._level_columns import (
    detect_level_codes,
    detect_level_columns,
    group_families_by_level,
)
from topo_tools.core.schema_map._levels import level_prefix
from topo_tools.core.schema_map._target_schema import TargetSchema


def _depth_column_sql(code_columns: dict[int, str], depth_column: str) -> str:
    """Build a CASE expression stamping the deepest level with a non-NULL code."""
    cases = "\n".join(
        f'WHEN "{code_columns[lvl]}" IS NOT NULL THEN {lvl}'
        for lvl in sorted(code_columns, reverse=True)
    )
    return f'CASE {cases} END AS "{depth_column}"'


def _families(
    conn: DuckDBPyConnection,
    table_in: str,
    columns: list[str],
    levels: list[int],
    schema: TargetSchema | None,
) -> tuple[dict[int, str], list[dict[int, str]]]:
    """Each level's code column, and every column family to cascade down."""
    if schema is not None:
        code_prefix = level_prefix(schema)
        name_prefix = field_prefix(schema.name_field)
        code_suffix = schema.code_field.split("{n}", 1)[1]
        code_columns: dict[int, str] = {}
        families: list[dict[int, str]] = []
        for prefix in dict.fromkeys([code_prefix, name_prefix]):
            family_group = column_families(columns, levels, prefix)
            if prefix == code_prefix:
                code_columns = family_group.get(code_suffix, {})
            families.extend(family_group.values())
        return code_columns, families

    level_columns = detect_level_columns(conn, table_in)
    code_columns = {
        lvl: c for lvl, c in detect_level_codes(conn, table_in).items() if lvl in levels
    }
    families = list(group_families_by_level(conn, table_in, level_columns).values())
    return code_columns, families


def main(  # noqa: PLR0913
    conn: DuckDBPyConnection,
    table_in: str,
    table_out: str,
    *,
    levels: list[int],
    schema: TargetSchema | None,
    depth_column: str,
) -> None:
    """Build table_out: stamp each row's real depth, fill every column family to it.

    A None schema triggers structural auto-detection of each column family.
    """
    columns = [row[0] for row in conn.execute(f'DESCRIBE "{table_in}"').fetchall()]
    if depth_column in columns:
        msg = f"depth_column {depth_column!r} already exists on {table_in!r}"
        raise ValueError(msg)

    code_columns, families = _families(conn, table_in, columns, levels, schema)

    filled_columns: set[str] = set()
    filled_select_parts: list[str] = []
    for per_level in families:
        filled_columns.update(per_level.values())
        if len(per_level) == 1:
            (only_column,) = per_level.values()
            filled_select_parts.append(f'"{only_column}"')
            continue
        fallback_cases = "\n".join(
            f'WHEN "{depth_column}" >= {lvl} THEN "{per_level[lvl]}"'
            for lvl in sorted(per_level, reverse=True)
        )
        fallback = f"CASE {fallback_cases} END"
        for level, column in sorted(per_level.items()):
            filled_select_parts.append(
                f'CASE WHEN "{depth_column}" >= {level} '
                f'THEN "{column}" ELSE ({fallback}) END AS "{column}"'
            )

    select_parts = (
        [f'"{c}"' for c in columns if c not in filled_columns]
        + filled_select_parts
        + [f'"{depth_column}"']
    )

    select_sql = ", ".join(select_parts)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{table_out}" AS
        WITH "depth" AS (
            SELECT *, {_depth_column_sql(code_columns, depth_column)}
            FROM "{table_in}"
        )
        SELECT {select_sql} FROM "depth"
    """)
