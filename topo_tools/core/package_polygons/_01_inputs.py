"""Imports geodata and reprojects to EPSG:4326, without auto-cleaning coverage."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from topo_tools.core.constants import is_noise_column
from topo_tools.core.io import read_and_reproject


def main(conn: DuckDBPyConnection, name: str, path: Path | str) -> None:
    """Read geodata into `{name}_01`, reprojected to EPSG:4326, uncleaned.

    Also strips ArcGIS/export-tool artifact columns, since this table doubles
    as the finest level's own output.
    """
    read_and_reproject(conn, name, path)
    table = f"{name}_01"
    columns = [row[0] for row in conn.execute(f'DESCRIBE "{table}"').fetchall()]
    noise = [c for c in columns if c not in {"fid", "geom"} and is_noise_column(c)]
    for c in noise:
        conn.execute(f'ALTER TABLE "{table}" DROP "{c}"')
