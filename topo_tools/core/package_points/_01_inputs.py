"""Imports geodata and reprojects to EPSG:4326, merging micro-polygons only."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from topo_tools.core.coverage import merge_micro_polygons
from topo_tools.core.io import read_and_reproject


def main(conn: DuckDBPyConnection, name: str, path: Path | str) -> None:
    """Read geodata into `{name}_01`, in EPSG:4326, micro-polygons merged."""
    read_and_reproject(conn, name, path)
    table = f"{name}_01"
    merge_micro_polygons(conn, table, table, issues_table=f"{name}_01_micro")
    conn.execute(f'DROP TABLE IF EXISTS "{name}_01_micro"')
