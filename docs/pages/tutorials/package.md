---
title: "package"
---

Runs `package-polygons`, `package-points`, and `package-lines` against one
input in a single call, for the common case of wanting the full
cartographic bundle at once.

### Example 1: defaults for all three outputs

Each sub-tool falls back to its own default naming
(`_admin{n}`/`_points`/`_lines`):

    topo-tools package adm3.geojson

### Example 2: explicit output template

`{x}` MUST appear in `--output` if given; it's substituted per sub-tool
(`admin{n}`, `points`, `lines`):

    topo-tools package adm3.geojson --output "web/{x}.geojson"
