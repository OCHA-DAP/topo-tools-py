"""topo-tools: DuckDB-powered geospatial topology utilities."""

from .api import (
    change,
    edge_clip,
    edge_extend,
    edge_match,
    edge_mosaic,
    edge_stitch,
    name_clean,
    name_detect,
    package,
    package_lines,
    package_points,
    package_polygons,
    schema_fill,
    schema_join,
    schema_map,
    topo_clean,
    topo_detect,
)
from .cli.main import cli

__all__ = [
    "change",
    "cli",
    "edge_clip",
    "edge_extend",
    "edge_match",
    "edge_mosaic",
    "edge_stitch",
    "name_clean",
    "name_detect",
    "package",
    "package_lines",
    "package_points",
    "package_polygons",
    "schema_fill",
    "schema_join",
    "schema_map",
    "topo_clean",
    "topo_detect",
]
