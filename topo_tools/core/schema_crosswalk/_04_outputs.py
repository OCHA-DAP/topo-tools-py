"""Exports the crosswalk CSV and/or mapped output, reusing map's/refactor's writers."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from topo_tools.core.schema_map import _03_outputs as map_outputs
from topo_tools.core.schema_refactor import _03_outputs as refactor_outputs


def main(
    conn: DuckDBPyConnection,
    name: str,
    crosswalk_path: Path | None,
    output_path: Path | None,
    *,
    debug: bool = False,
) -> None:
    """Export `{name}_02` to crosswalk_path and `{name}_apply_02` to output_path."""
    if crosswalk_path is not None:
        map_outputs.main(conn, name, crosswalk_path, debug=debug)
    if output_path is not None:
        refactor_outputs.main(conn, f"{name}_apply", output_path, debug=debug)
    if not debug:
        for t in (f"{name}_01", f"{name}_02"):
            conn.execute(f'DROP TABLE IF EXISTS "{t}"')
