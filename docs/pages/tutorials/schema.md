---
status: draft
title: "Schema"
---

Crosswalk a source file's columns onto a target admin-hierarchy schema
(`adm{n}_name`/`adm{n}_code` by default), copy missing ancestor columns
from a parent layer, then fill the hierarchy down to each row's real
depth.

## Map and rename columns

Propose a crosswalk and apply it in one call:

    topo-tools schema-crosswalk example.geojson

This writes the renamed output plus `example_crosswalk.csv`. Review and
hand-edit the crosswalk, then re-apply it with `schema-refactor` alone,
without re-running the mapping:

    topo-tools schema-refactor example.geojson example_crosswalk.csv --overwrite

`schema-crosswalk` is `schema-map` (propose the crosswalk) followed by
`schema-refactor` (apply it); run `schema-map` on its own to review the
crosswalk before anything is renamed.

## Copy ancestor columns from a parent layer

A layer missing an ancestor level's columns entirely gets them from the
parent layer it overlaps most. Chain levels coarsest-first:

    topo-tools schema-join admin2.parquet admin1.parquet admin2_join.parquet
    topo-tools schema-join admin3.parquet admin2_join.parquet admin3_join.parquet

## Fill the hierarchy down

Run `schema-fill` against an already-clipped/stitched layer (an
`edge-match`/`edge-mosaic` output):

    topo-tools schema-fill admin3_join.parquet

This stamps a new `adm_lvl` column (rename it with `--depth-column`) and
fills every level's name/code columns down to that depth, per row, so a
genuine `NULL` at a row's own real depth stays `NULL` rather than being
backfilled from a shallower ancestor.

See the [`schema-map`](../reference/schema_map/),
[`schema-refactor`](../reference/schema_refactor/),
[`schema-crosswalk`](../reference/schema_crosswalk/),
[`schema-join`](../reference/schema_join/), and
[`schema-fill`](../reference/schema_fill/) references for details.
