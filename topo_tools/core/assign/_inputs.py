"""Loads the (possibly multi-file) input layer and the overlay layer, both raw."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from topo_tools.core.io import read_and_reproject, reproject_select_sql


def load_input(
    conn: DuckDBPyConnection, name: str, input_paths: list[Path | str]
) -> None:
    """Load/combine the (possibly multi-file) input polygons, uncleaned.

    Each part is tagged with its own full path as `source_file` (basename
    alone can't distinguish same-named files across directories).
    """
    union_sql = " UNION ALL BY NAME ".join(
        f"(SELECT *, '{path}' AS source_file FROM ({reproject_select_sql(conn, path)}))"
        for path in input_paths
    )
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_input_01" AS
        SELECT * EXCLUDE (fid), row_number() OVER () AS fid
        FROM ({union_sql})
    """)


def load_overlay(conn: DuckDBPyConnection, name: str, overlay_path: Path | str) -> None:
    """Load the overlay layer, uncleaned."""
    read_and_reproject(conn, f"{name}_overlay", overlay_path)


def load_original(
    conn: DuckDBPyConnection, name: str, original_paths: list[Path | str]
) -> None:
    """Expose the original layer's unvalidated geometry as view `{name}_original_01`."""
    union_sql = " UNION ALL ".join(
        f"(SELECT geom FROM ({reproject_select_sql(conn, path, make_valid=False)}))"
        for path in original_paths
    )
    conn.execute(f"""--sql
        CREATE OR REPLACE VIEW "{name}_original_01" AS
        SELECT row_number() OVER () AS fid, geom FROM ({union_sql})
    """)
