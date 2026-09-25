---
status: draft
title: "Edge"
---

Fit a finer child layer (e.g. admin3) into a coarser parent/clip layer
(e.g. admin0), with no gap or overhang at the edge, then re-fit it when
the parent layer changes.

## Fit a raw layer to its parent

`edge-match` extends each child outward with Voronoi diagrams, then clips
it to its parent, in one call:

    topo-tools edge-match adm3.gpkg adm0.gpkg adm3_matched.gpkg \
      --issues-file match_report.gpkg

Add `--fill-schema` to cascade admin-hierarchy columns down to each row's
real depth before export.

## Re-fit to a new parent

When only the parent/clip layer changes, `edge-mosaic` re-clips an
already-fitted layer against it, skipping Voronoi extension entirely:

    topo-tools edge-mosaic adm3_matched.gpkg adm0_new.gpkg adm3_mosaicked.gpkg \
      --issues-file mosaic_report.gpkg

## The primitives underneath

`edge-match` and `edge-mosaic` chain three primitives, each also
runnable on its own for a narrower job: `edge-extend` (extend a layer
outward with no parent to fit), `edge-clip` (assign each child to a
parent and clip it), and `edge-stitch` (close seams in an already-tiled
layer).

See the [`edge-match`](../reference/edge_match/),
[`edge-mosaic`](../reference/edge_mosaic/),
[`edge-extend`](../reference/edge_extend/),
[`edge-clip`](../reference/edge_clip/), and
[`edge-stitch`](../reference/edge_stitch/) references for details.
