---
title: "schema-join"
sidebar:
  order: 8
  badge:
    text: Draft
    variant: caution
---

`schema-join` copies a join layer's admin-hierarchy columns onto every
input feature it overlaps most, without touching geometry (e.g. an admin3 file
carrying only `adm3_code`/`adm3_name` gets `adm2_code`/`adm2_name`/
`adm1_code`/`adm1_name` from an admin2 file that carries its own
ancestors). Given an explicit `name_field`/`code_field` pair, it finds the
join layer's hierarchy columns through `schema-map`'s `TargetSchema` mechanism
(`docs/dev/explanation/1-schema/schema_map.md`); omitting both triggers structural
auto-detection on the join layer instead. Only the join layer is scanned for
hierarchy columns: the input layer's own columns are compared against them, never
detected.

## Why this exists

A normalized schema needs every ancestor code on every row, but a source
file often carries only its own level's code, sometimes with its ancestors'
names. `schema-fill` can't help, since it only cascades values already on
the row. `edge-match --merge --overlay-include` does copy overlay columns, but
it also extends and clips every input feature to its overlay feature, which is the wrong
tool for a layer whose geometry is already final. Truncating an input feature's code
to derive its join feature's only works when codes nest, and fails silently when
they don't. `schema-join` derives the join feature from geometry instead, and
reports every case where that derivation is weak or disagrees with a value
the input feature already has.

## Chaining levels

A join file that already carries its own ancestors fills every level in
one call. Otherwise, chain calls coarsest-first: admin2 against admin1,
then admin3 against the joined admin2 output, so each call's join layer already
has everything above it.

## Pipeline

Tables are named `{input}_schema_join_*`.

1. **`_01_inputs`**: loads the input layer via `core.assign.load_input()`
   (`{name}_input_01`, a fresh `fid` plus `source_file`) and the join layer via
   `core.assign.load_overlay()` (`{name}_overlay_01`), both reprojected to
   EPSG:4326.
2. **`_02_assign`**: calls `core.assign.assign_many()` unchanged, pairing
   each input feature with the join feature it shares the most area with
   (`{name}_02_assign`, `{name}_02_pairs`, `{name}_02_unassigned`), then
   builds `{name}_02_share`: each input feature's own equal-area area and the
   share its assigned join feature covers.
3. **`_03_join`**: resolves the join layer's hierarchy columns, then builds
   `{name}_03` by left-joining each input feature to its assigned join feature, adding
   each column absent from the input layer, skipping each one identical on every
   assigned input feature, and adding the join feature's values under a numbered sibling
   name for each one that differs (`{name}_03_mismatch` records the
   differing values). Geometry passes through unchanged. The input layer's
   columns keep their order, each added sibling follows its own column,
   and new-level columns follow in `core.admin_columns.canonical_order()`;
   rows are sorted by the deepest level's code.
4. **`_04_outputs`**: builds `{name}_04` (`no-overlap`, `low-overlap`,
   `value-mismatch` rows, in the shared issues-table column schema) and
   exports the joined layer and its issues file. There is no topology
   check, since geometry is never modified.

## Why per-feature plurality, not per-file majority

`edge-match` and `edge-mosaic` default to `assign_one`, forcing a whole
input file onto one majority-vote overlay feature, since each of their input files
normally sits inside a single overlay feature. A `schema-join` input file is the
opposite case: an admin3 file spans every admin2 unit, so each input feature needs
its own join feature, which is exactly `assign_many`'s per-feature plurality
(`docs/dev/explanation/3-edge/assign.md`).

## Why a low-overlap input feature is flagged, not rejected

When an input feature's best join feature covers less than `min_overlap` (default `0.5`)
of its area, no single join feature holds a majority of it, which usually means
the two layers' boundaries were digitized differently or the input feature
genuinely straddles a join boundary. The plurality pick is still the most
likely join feature, so it is kept; the `low-overlap` row, with the uncovered
area in `area_m2`, marks it for review rather than blocking the run.

## Why a conflicting value is kept side by side

An input feature's own value and its join feature's are both source data, and neither is
reliably correct (e.g. a name spelled with an accent in one layer and
without it in the other). `schema-join` keeps the input layer's column untouched,
adds the join feature's values as the next free numbered sibling (`adm2_name1`),
and writes a `value-mismatch` row per differing input feature, leaving the choice
to a later review step (see `docs/adr/0109`).
