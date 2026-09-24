"""Loads the child and parent layers, both raw."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from topo_tools.core.assign import load_children, load_parent


def main(
    conn: DuckDBPyConnection,
    name: str,
    child_path: Path | str,
    parent_path: Path | str,
) -> None:
    """Load `{name}_child_01` and `{name}_parent_01`."""
    load_children(conn, name, [child_path])
    load_parent(conn, name, parent_path)
