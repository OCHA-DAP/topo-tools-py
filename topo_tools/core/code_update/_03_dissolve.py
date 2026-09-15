"""Dissolves OLD and NEW into one level, independently, for classify."""

from duckdb import DuckDBPyConnection

from topo_tools.core.code_update._02_levels import SideLevels
from topo_tools.core.dissolve import _02_dissolve as dissolve_stage


def _dissolve_side(
    conn: DuckDBPyConnection, table: str, dest: str, level: int, side: SideLevels
) -> None:
    """Dissolve one side's finest table into dest, grouped by level's own column."""
    if side.schema is not None:
        dissolve_stage.main(
            conn,
            table,
            dest,
            group_by=[side.schema.code_field.format(n=level)],
            target_schema=side.schema,
        )
        return

    cluster = side.level_columns[level]
    exclude = [
        c
        for lvl, cols in side.level_columns.items()
        if lvl > level
        for c in cols.identity_columns
    ]
    dissolve_stage.main(conn, table, dest, group_by=cluster.group_by, exclude=exclude)


def main(  # noqa: PLR0913
    conn: DuckDBPyConnection,
    name: str,
    old_table: str,
    new_table: str,
    n: int,
    *,
    side_a: SideLevels,
    side_b: SideLevels,
) -> None:
    """Dissolve `{name}_dsl_{n}_a`/`_b` for level n."""
    _dissolve_side(conn, old_table, f"{name}_dsl_{n}_a", n, side_a)
    _dissolve_side(conn, new_table, f"{name}_dsl_{n}_b", n, side_b)
