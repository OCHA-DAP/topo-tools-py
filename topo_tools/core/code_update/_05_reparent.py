"""Re-derives one finer NEW level's true parent spatially, not from a stale column."""

from duckdb import DuckDBPyConnection

from topo_tools.core.assign import assign_many


def main(conn: DuckDBPyConnection, name: str, n: int, prev_level: int) -> None:
    """Write `{name}_reparent_{n}_02_assign`: each NEW fid's true parent fid."""
    reparent_name = f"{name}_reparent_{n}"
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{reparent_name}_child_01" AS
        SELECT fid, geom, 'child' AS source_file FROM "{name}_dsl_{n}_b"
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{reparent_name}_parent_01" AS
        SELECT fid, geom, 'parent' AS source_file FROM "{name}_dsl_{prev_level}_b"
    """)
    assign_many(conn, reparent_name)
    conn.execute(f'DROP TABLE IF EXISTS "{reparent_name}_child_01"')
    conn.execute(f'DROP TABLE IF EXISTS "{reparent_name}_parent_01"')
    conn.execute(f'DROP TABLE IF EXISTS "{reparent_name}_02_unassigned"')
