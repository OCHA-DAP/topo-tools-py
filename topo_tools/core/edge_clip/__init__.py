"""Clip tool: clips each input polygon to its assigned overlay polygon's geometry."""

from ._engine import main
from ._tiling import subdivide_boundary

__all__ = ["main", "subdivide_boundary"]
