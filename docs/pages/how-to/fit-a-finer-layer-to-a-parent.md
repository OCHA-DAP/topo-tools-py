---
title: "Fit a finer layer to a coarser parent"
---

Extend and clip a finer child layer (e.g. admin3) so it fits a coarser
parent/clip layer (e.g. admin0/admin1) exactly, with no gap or overhang at
the edge.

If the child layer hasn't been extended yet (a raw digitized delivery),
use `edge-match`; it extends and clips in one call:

    topo-tools edge-match adm3.gpkg adm2.gpkg adm3_matched.gpkg \
      --issues-file match_report.gpkg

If the child layer is already a prior `edge-extend`/`edge-match` output
and only the parent/clip layer has changed, use `edge-mosaic` instead; it
skips Voronoi extension entirely and just re-clips:

    topo-tools edge-mosaic adm3_extended.parquet adm0_new.geojson \
      adm3_mosaicked.parquet --issues-file mosaic_report.parquet

Both accept `--fill-schema` to cascade admin-hierarchy columns down to
each row's real depth before export, and both accept multiple children
files (`--input`, repeatable/comma-separated) when children genuinely
scatter across more than one parent.

See [`edge-match` reference](../reference/edge_match/),
[`edge-mosaic` reference](../reference/edge_mosaic/), and their
explanation pages for the assign/extend/clip/stitch pipeline each one
chains internally.
