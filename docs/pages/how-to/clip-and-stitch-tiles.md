---
title: "Clip children to a parent, or stitch tiled seams"
---

Use the two lower-level primitives `edge-match`/`edge-mosaic` chain
internally, directly, for a narrower job than a full fit.

Clip a children layer to a single parent/clip layer's geometry (assigning
each child to its parent first):

    topo-tools edge-clip children.parquet adm1.geojson clipped.parquet \
      --issues-file clip_report.parquet

To clip several children files against one shared parent load, repeat/
comma-split `--input`/`--output` and give `--name`:

    topo-tools edge-clip afg.parquet world_adm0.geojson afg_out.parquet \
      --input ago.parquet,are.parquet --output ago_out.parquet,are_out.parquet \
      --name portolan_batch

Close seams left in an already-tiled layer (e.g. several clipped tiles
combined) with one whole-table coverage-clean pass:

    topo-tools edge-stitch "tmp/clipped/*.parquet" stitched.parquet \
      --issues-file stitch_report.parquet

See [`edge-clip` reference](../reference/edge_clip/) and
[`edge-stitch` reference](../reference/edge_stitch/) for when to reach
for these instead of `edge-match`/`edge-mosaic`.
