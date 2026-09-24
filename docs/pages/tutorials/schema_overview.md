---
title: "Schema"
---

Learn how to crosswalk a source file's columns onto a target schema,
copy missing ancestor columns from a parent layer, then fill the admin
hierarchy down.

- [schema-map](schema_map/): propose a source-column to target-schema
  crosswalk.
- [schema-refactor](schema_refactor/): apply a crosswalk, renaming/
  dropping columns.
- [schema-crosswalk](schema_crosswalk/): map and apply a crosswalk in
  one call.
- [schema-fill](schema_fill/): stamp each row's real depth and cascade
  hierarchy columns down.
- [schema-join](schema_join/): copy each child's best-overlapping parent's
  hierarchy columns onto it.
