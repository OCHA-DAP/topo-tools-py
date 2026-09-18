---
title: "package-lines"
---

Produces one deduplicated line network of admin boundaries (shared between
two units, or exterior to all of them), tagged by adjacency and the
coarsest admin level each segment belongs to.

### Example 1: default naming

Produces `adm3_lines.geojson`, combining shared and exterior boundaries
from every detected level, deduplicated so no segment repeats:

    topo-tools package-lines adm3.geojson

### Example 2: style by boundary depth

`adm_lvl` (or a custom `--depth-column`) lets a web map style an
international boundary (level 0) differently from a sub-national one:

    topo-tools package-lines adm3.geojson --depth-column boundary_level
