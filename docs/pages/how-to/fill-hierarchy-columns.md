---
title: "Fill hierarchy columns down to each row's real depth"
---

Stamp each row with its real admin depth, then cascade every
admin-hierarchy column down to that depth, run against an
already-clipped/stitched layer (an `edge-match`/`edge-mosaic` output). A
layer missing an ancestor level's columns entirely needs `schema-join`
against that parent layer first, since `schema-fill` only cascades values
already on the row.

    topo-tools schema-fill admin4.parquet --name-field state_name --code-field state_code

This stamps a new `adm_lvl` column (rename it with `--depth-column`) and
fills every level's name/code columns down to that depth, per row, so a
genuine `NULL` at a row's own real depth stays `NULL` rather than being
backfilled from a shallower ancestor. Level columns are auto-detected
structurally when `--name-field`/`--code-field` are omitted.

Run `package-polygons` afterward to dissolve every level normally; it
carries the stamped depth column through automatically.

See [`schema-fill` reference](../reference/schema_fill/) and its
explanation page for the pinned-fill rule in detail.
