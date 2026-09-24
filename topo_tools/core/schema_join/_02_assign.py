"""Pairs each child with its plurality-overlap parent, and that parent's area share."""

from duckdb import DuckDBPyConnection

from topo_tools.core.assign import assign_many
from topo_tools.core.constants import EQUAL_AREA_CRS


def main(conn: DuckDBPyConnection, name: str) -> None:
    """Build `{name}_02_assign` plus `{name}_02_share` (best-parent area share)."""
    assign_many(conn, name)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02_share" AS
        WITH areas AS (
            SELECT fid AS child_fid,
                   ST_Area(ST_Transform(geom, 'EPSG:4326', '{EQUAL_AREA_CRS}'))
                       AS child_area
            FROM "{name}_child_01"
        )
        SELECT a.child_fid, a.parent_fid, areas.child_area, p.shared_area,
               p.shared_area / NULLIF(areas.child_area, 0) AS overlap_share
        FROM "{name}_02_assign" a
        JOIN areas USING (child_fid)
        JOIN "{name}_02_pairs" p
          ON p.child_fid = a.child_fid AND p.parent_fid = a.parent_fid
    """)
