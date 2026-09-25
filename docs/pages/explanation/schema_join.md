---
status: draft
title: "schema-join"
---

`schema-join` copies a parent layer's admin-hierarchy columns onto every
child it overlaps most, without touching geometry (e.g. an admin3 file
carrying only `adm3_code`/`adm3_name` gets `adm2_code`/`adm2_name`/
`adm1_code`/`adm1_name` from an admin2 file that carries its own
ancestors). Given an explicit `name_field`/`code_field` pair, it finds the
parent's hierarchy columns through `schema-map`'s `TargetSchema` mechanism
(`docs/explanation/schema_map.md`); omitting both triggers structural
auto-detection on the parent instead. Only the parent is scanned for
hierarchy columns: the child's own columns are compared against them, never
detected.

## Why this exists

A normalized schema needs every ancestor code on every row, but a source
file often carries only its own level's code, sometimes with its ancestors'
names. `schema-fill` can't help, since it only cascades values already on
the row. `edge-match --merge --parent-include` does copy parent columns, but
it also extends and clips every child to its parent, which is the wrong
tool for a layer whose geometry is already final. Truncating a child's code
to derive its parent's only works when codes nest, and fails silently when
they don't. `schema-join` derives the parent from geometry instead, and
reports every case where that derivation is weak or disagrees with a value
the child already has.

## Chaining levels

A parent file that already carries its own ancestors fills every level in
one call. Otherwise, chain calls coarsest-first: admin2 against admin1,
then admin3 against the joined admin2 output, so each call's parent already
has everything above it.

## Pipeline

Tables are named `{input}_schema_join_*`.

1. **`_01_inputs`**: loads the child via `core.assign.load_children()`
   (`{name}_child_01`, a fresh `fid` plus `source_file`) and the parent via
   `core.assign.load_parent()` (`{name}_parent_01`), both reprojected to
   EPSG:4326.
2. **`_02_assign`**: calls `core.assign.assign_many()` unchanged, pairing
   each child with the parent it shares the most area with
   (`{name}_02_assign`, `{name}_02_pairs`, `{name}_02_unassigned`), then
   builds `{name}_02_share`: each child's own equal-area area and the
   share its assigned parent covers.
3. **`_03_join`**: resolves the parent's hierarchy columns, then builds
   `{name}_03` by left-joining each child to its assigned parent, adding
   each column absent from the child, skipping each one identical on every
   assigned child, and adding the parent's values under a numbered sibling
   name for each one that differs (`{name}_03_mismatch` records the
   differing values). Geometry passes through unchanged. Columns follow
   `core.admin_columns.canonical_order()`, and rows are sorted by the
   deepest level's code.
4. **`_04_outputs`**: builds `{name}_04` (`no-parent`, `low-overlap`,
   `value-mismatch` rows, in the shared issues-table column schema) and
   exports the joined layer and its issues file. There is no topology
   check, since geometry is never modified.

## Why per-child plurality, not per-file majority

`edge-match` and `edge-mosaic` default to `assign_one`, forcing a whole
child file onto one majority-vote parent, since each of their child files
normally sits inside a single parent. A `schema-join` child file is the
opposite case: an admin3 file spans every admin2 unit, so each child needs
its own parent, which is exactly `assign_many`'s per-child plurality
(`docs/explanation/assign.md`).

## Why a low-overlap child is flagged, not rejected

When a child's best parent covers less than `min_overlap` (default `0.5`)
of its area, no single parent holds a majority of it, which usually means
the two layers' boundaries were digitized differently or the child
genuinely straddles a parent boundary. The plurality pick is still the most
likely parent, so it is kept; the `low-overlap` row, with the uncovered
area in `area_m2`, marks it for review rather than blocking the run.

## Why a conflicting value is kept side by side

A child's own value and its parent's are both source data, and neither is
reliably correct (e.g. a name spelled with an accent in one layer and
without it in the other). `schema-join` keeps the child's column untouched,
adds the parent's values as the next free numbered sibling (`adm2_name1`),
and writes a `value-mismatch` row per differing child, leaving the choice
to a later review step (see `docs/adr/0109`).
