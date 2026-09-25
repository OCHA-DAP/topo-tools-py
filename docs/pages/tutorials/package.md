---
status: draft
title: "Package"
---

Derive the cartographic outputs a web map needs (dissolved coarser
levels, label points, deduplicated boundary lines) from one clean polygon
layer.

## Package everything at once

    topo-tools package adm3.geojson --output "web/{x}.geojson"

`{x}` is substituted per output (`admin{n}`, `points`, `lines`).

## Package one output at a time

Run each sub-tool on its own when only one output is needed:

    topo-tools package-polygons adm3.geojson
    topo-tools package-points adm3.geojson
    topo-tools package-lines adm3.geojson

`package-polygons` dissolves into every detected coarser level
(`adm3_admin1.geojson`, `adm3_admin2.geojson`, ...). `package-points`
produces one label point per admin unit per level, using the pole of
inaccessibility so a label always lands on its own territory.
`package-lines` produces one deduplicated boundary-line network, tagged
by adjacency and the coarsest level each segment belongs to, so a web map
can style an international boundary differently from a sub-national one.

See the [`package`](../reference/package/),
[`package-polygons`](../reference/package_polygons/),
[`package-points`](../reference/package_points/), and
[`package-lines`](../reference/package_lines/) references for level
detection and output naming.
