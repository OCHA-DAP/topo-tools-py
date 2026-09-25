---
status: draft
title: "Edge"
---

Why edge-match and edge-mosaic are both built from the same three
primitives (edge-extend, edge-clip, edge-stitch), and when to reach for a
primitive directly instead.

- [edge-extend](edge_extend/): Voronoi extension, the standalone
  primitive.
- [edge-clip](edge_clip/): assign-then-clip, the standalone primitive.
- [edge-stitch](edge_stitch/): whole-table coverage-clean, the
  standalone primitive.
- [edge-match](edge_match/): extend and clip a raw finer layer into a
  coarser parent.
- [edge-mosaic](edge_mosaic/): re-clip an already-extended layer into a
  new parent, skipping extension.
