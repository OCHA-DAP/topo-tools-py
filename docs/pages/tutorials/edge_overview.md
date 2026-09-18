---
title: "Edge"
---

Learn how to extend, clip, and stitch boundary layers so a finer layer
fits a coarser one with no gaps or overhang.

- [edge-extend](edge_extend/): extend a layer outward with Voronoi
  diagrams to fill gaps.
- [edge-clip](edge_clip/): assign each child to its parent, then clip it
  to that parent's geometry.
- [edge-stitch](edge_stitch/): close seams in an already-tiled layer.
- [edge-match](edge_match/): extend and clip a raw finer layer into a
  coarser parent in one call.
- [edge-mosaic](edge_mosaic/): re-clip an already-extended layer into a
  new parent layer.
