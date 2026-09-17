---
title: "schema-crosswalk"
---

Maps a source-column -> target-schema crosswalk, then immediately
applies it, writing both the crosswalk CSV and the renamed/dropped-column
mapped output in one call (`schema-map` + `schema-refactor` in one step).

### Example 1: basic run, default (`adm{n}_name`/`adm{n}_code`) naming, output names chosen automatically

    topo-tools schema-crosswalk example.geojson

### Example 2: custom target naming

    topo-tools schema-crosswalk example.geojson --name-field state_name --code-field state_code

### Example 3: explicit outputs

    topo-tools schema-crosswalk example.gpkg example_mapped.gpkg example_crosswalk.csv --name-field state_name --code-field state_code

### Example 4: iterate on a hand-edited crosswalk

    topo-tools schema-crosswalk example.geojson
    # review/edit example_crosswalk.csv, then re-apply without re-mapping:
    topo-tools schema-refactor example.geojson example_crosswalk.csv --overwrite

See `docs/tutorials/schema_map.md`/`docs/tutorials/schema_refactor.md` for the two
underlying tools this composes.
