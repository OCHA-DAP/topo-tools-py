---
title: "Package a layer for a web map"
---

Derive the cartographic outputs a web map needs (dissolved coarser
levels, label points, deduplicated boundary lines) from one clean polygon
layer.

Run all three at once:

    topo-tools package adm3.geojson --output "web/{x}.geojson"

Or run each independently, when only one output is needed:

    topo-tools package-polygons adm3.geojson
    topo-tools package-points adm3.geojson
    topo-tools package-lines adm3.geojson

`package-polygons` dissolves into every detected coarser level
(`adm3_admin1.geojson`, `adm3_admin2.geojson`, ...). `package-points`
produces one label point per admin unit per level, using the pole of
inaccessibility so a label always lands on its own territory.
`package-lines` produces one deduplicated boundary-line network, tagged
by adjacency and the coarsest level each segment belongs to, useful for
styling an international boundary differently from a sub-national one via
`--depth-column`.

See [`package` reference](../reference/package/),
[`package-polygons` reference](../reference/package_polygons/),
[`package-points` reference](../reference/package_points/), and
[`package-lines` reference](../reference/package_lines/) for level
auto-detection and output naming details.
