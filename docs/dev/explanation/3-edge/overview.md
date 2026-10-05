---
title: "Edge"
sidebar:
  order: 8
  label: "Overview"
  badge:
    text: Draft
    variant: caution
---

Why edge-match and edge-mosaic are both built from the same three
primitives (edge-extend, edge-clip, edge-stitch), and when to reach for a
primitive directly instead.

- [edge-extend](edge_extend.md): Voronoi extension, the standalone
  primitive.
- [edge-clip](edge_clip.md): assign-then-clip, the standalone primitive.
- [edge-stitch](edge_stitch.md): whole-table coverage-clean, the
  standalone primitive.
- [edge-match](edge_match.md): extend and clip a raw finer layer into a
  coarser overlay polygon.
- [edge-mosaic](edge_mosaic.md): re-clip an already-extended layer into a
  new overlay polygon, skipping extension.
