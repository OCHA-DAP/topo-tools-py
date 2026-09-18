---
title: "Extend a layer outward to fill gaps"
---

Extend a polygon layer's boundaries outward using Voronoi diagrams,
producing a complete coverage layer with no external gaps (coastlines,
disputed areas, water bodies).

    topo-tools edge-extend example.gpkg example_extended.gpkg

Rerun and overwrite a previous output:

    topo-tools edge-extend example.parquet example_extended.parquet --overwrite

This is the standalone primitive `edge-match` calls per parent group
internally; reach for it directly only when a layer needs extending on
its own, with no parent/clip layer to fit afterward. If a parent/clip
layer exists, use `edge-match` instead so extend and clip happen in one
call.

See [`edge-extend` reference](../reference/edge_extend/) and its
explanation page for how the Voronoi extension itself works.
