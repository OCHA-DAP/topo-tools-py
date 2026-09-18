---
title: "Map and rename columns to a target schema"
---

Crosswalk a source file's columns onto a target admin-hierarchy schema
(`adm{n}_name`/`adm{n}_code` by default), then rename/drop columns to
match.

Propose a crosswalk first, without renaming anything:

    topo-tools schema-map example.geojson --name-field state_name --code-field state_code

This writes a crosswalk CSV. Review and hand-edit it, then apply it
separately:

    topo-tools schema-refactor example.geojson crosswalk.csv

To see mapped values right away and iterate without re-running the
mapping step every time, use `schema-crosswalk` (`schema-map` +
`schema-refactor` in one call), then re-apply a hand-edited crosswalk with
`schema-refactor` alone:

    topo-tools schema-crosswalk example.geojson
    # review/edit example_crosswalk.csv, then re-apply without re-mapping:
    topo-tools schema-refactor example.geojson example_crosswalk.csv --overwrite

See [`schema-map` reference](../reference/schema_map/),
[`schema-refactor` reference](../reference/schema_refactor/), and
[`schema-crosswalk` reference](../reference/schema_crosswalk/) for how
level detection and the crosswalk file format work.
