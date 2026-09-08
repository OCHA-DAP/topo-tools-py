"""Dissolves the finest layer into every coarser detected admin level."""

from duckdb import DuckDBPyConnection

from topo_tools.core.dissolve import _02_dissolve as dissolve_stage
from topo_tools.core.schema_map._target_schema import TargetSchema


def main(
    conn: DuckDBPyConnection,
    name: str,
    levels: list[int],
    schema: TargetSchema,
) -> None:
    """Dissolve `{name}_01` into `{name}_02_{n}` for every level but the finest.

    The finest level needs no dissolve pass: it's already at that
    granularity, so its own output is `{name}_01` directly.
    """
    finest = max(levels)
    for n in levels:
        if n == finest:
            continue
        dissolve_stage.main(
            conn,
            f"{name}_01",
            f"{name}_02_{n}",
            group_by=[schema.code_field.format(n=n)],
            target_schema=schema,
        )
