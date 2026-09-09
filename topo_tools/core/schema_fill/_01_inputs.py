"""Imports leaf-level geodata, validating every hierarchy level has a code column."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from topo_tools.core.io import read_and_reproject
from topo_tools.core.schema_map._level_columns import detect_level_columns
from topo_tools.core.schema_map._levels import detect_levels
from topo_tools.core.schema_map._target_schema import TargetSchema


def main(
    conn: DuckDBPyConnection, name: str, path: Path | str, schema: TargetSchema | None
) -> None:
    """Import geodata; raise ValueError early if a level lacks a code column.

    A None schema triggers structural auto-detection of each level instead.
    """
    read_and_reproject(conn, name, path)
    table = f"{name}_01"
    if schema is not None:
        detect_levels(conn, table, schema)
        return

    level_columns = detect_level_columns(conn, table)
    missing = [n for n, cols in level_columns.items() if not cols.has_code]
    if missing:
        msg = f"missing code column for level(s) {missing} in {table!r}"
        raise ValueError(msg)
