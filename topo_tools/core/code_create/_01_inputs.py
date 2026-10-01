"""Imports the one flat finest-level input."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from topo_tools.core.io import read_and_reproject


def main(conn: DuckDBPyConnection, name: str, path: Path | str) -> None:
    """Load and reproject path into `{name}_01`."""
    read_and_reproject(conn, name, path)
