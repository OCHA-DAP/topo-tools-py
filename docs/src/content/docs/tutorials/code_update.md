---
title: "code-update"
---

Reconciles an already-coded OLD layer against an uncoded NEW candidate:
classifies every unit (`change`'s own engine), then retains, replaces, or
retires its code per the standard changelog policy.

### Example 1: basic run, format auto-detected off OLD's own codes

    topo-tools code-update admin1_old.geojson admin1_new.geojson

### Example 2: identity-linking a relocated unit by source code

    topo-tools code-update old.gpkg new.gpkg --link-by-code \
      --code-column-a srcid --code-column-b srcid

### Example 3: explicit output paths, custom format override

Writes `admin1_new_coded.geojson` and `admin1_new_coded_changelog.csv`
unless given:

    topo-tools code-update old.parquet new.parquet coded.parquet changelog.csv \
      --root-code AFG --delimiter . --min-width 3
