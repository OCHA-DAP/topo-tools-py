---
title: "schema-map"
---

Maps a source-column -> target-schema crosswalk for one input file,
deterministically (no LLM). Never renames anything; review/edit the
crosswalk, then run `schema-refactor`.

### Example 1: basic run, default (`adm{n}_name`/`adm{n}_code`) naming, output name chosen automatically

    topo-tools schema-map example.geojson

### Example 2: custom target naming

    topo-tools schema-map example.geojson --name-field state_name --code-field state_code

### Example 3: explicit output

    topo-tools schema-map example.gpkg crosswalk.csv --name-field state_name --code-field state_code

### Example 4: number levels from the file's own admin level

    topo-tools schema-map admin3.geojson --level 3
