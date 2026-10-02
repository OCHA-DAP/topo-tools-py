"""Imports geodata and reprojects to EPSG:4326, names untouched."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from topo_tools.core.io import read_and_reproject


def main(conn: DuckDBPyConnection, name: str, path: Path | str) -> None:
    """Read geodata into `{name}_01`, reprojected to EPSG:4326."""
    read_and_reproject(conn, name, path)
