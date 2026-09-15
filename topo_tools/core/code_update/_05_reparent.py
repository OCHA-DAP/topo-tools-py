"""Re-derives each finer NEW level's true parent spatially, not from a stale column."""

import itertools

from duckdb import DuckDBPyConnection

from topo_tools.core.assign import assign_many
from topo_tools.core.code_update._02_levels import SideLevels


def main(conn: DuckDBPyConnection, name: str, *, side_b: SideLevels) -> None:
    """Write `{name}_reparent_{n}_02_assign`: each NEW fid's true parent fid."""
    levels = sorted(side_b.columns)
    for prev, n in itertools.pairwise(levels):
        reparent_name = f"{name}_reparent_{n}"
        conn.execute(f"""--sql
            CREATE OR REPLACE TABLE "{reparent_name}_child_01" AS
            SELECT fid, geom, 'child' AS source_file FROM "{name}_dsl_{n}_b"
        """)
        conn.execute(f"""--sql
            CREATE OR REPLACE TABLE "{reparent_name}_parent_01" AS
            SELECT fid, geom, 'parent' AS source_file FROM "{name}_dsl_{prev}_b"
        """)
        assign_many(conn, reparent_name)
        conn.execute(f'DROP TABLE IF EXISTS "{reparent_name}_child_01"')
        conn.execute(f'DROP TABLE IF EXISTS "{reparent_name}_parent_01"')
