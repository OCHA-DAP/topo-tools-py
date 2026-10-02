---
title: "schema-detect"
sidebar:
  order: 7
  badge:
    text: Draft
    variant: caution
---

`schema-detect` checks that one admin layer's columns form a consistent
hierarchy, without changing it. Every check is DuckDB SQL over a table of
level columns, so the same queries run in DuckDB-WASM.

## Stages

| Stage | Table | What it does |
| --- | --- | --- |
| `_01_inputs` | `{name}_01` | reads and reprojects the input |
| `_02_levels` | `{name}_02` | one row per level column (level, family, spelling, code or not), plus one row per level-wide problem |
| `_03_checks` | `{name}_03` | one SQL query per kind (`{name}_03_tmp{n}`), unioned |
| `_04_outputs` | `{name}_04` | keys and severity; writes CSV or Parquet |

## Level membership by naming

Structural detection (`detect_level_columns()`) groups columns by how
their values nest, which is right for finding levels but can fold one
level's columns into the next: on KGZ and LBN admin3 it merges every
`adm2_*` column into level 3, though adm2 nests cleanly. A layer then reads
as skipping level 2. So once the detected code columns share one naming
with the level number in it (`adm{n}_pcode`), `schema-detect` takes that
naming as the template and assigns every column to a level by name, the
same path an explicit `--code-field` takes. Structural membership remains
the fallback for namings without a level number (`state_code`,
`county_code`).

Names are compared ignoring case and separators, so `ADM2_PCODE` still
counts as level 2's code column and `adm1name1` as level 1's `name1`: both
are reported as `column-naming` instead of missing.

## Families and the column set

A column's family is its name without the level's prefix and number:
`adm2_name1` and `adm3_name1` are both `name1`. `column-set-mismatch`
reports a level missing a family that two or more other levels have. A
family at one level only is a level-specific attribute (`adm3_ref_name`,
`adm0_en`) and isn't reported, since in a two-level layer there is no way
to tell which level is the odd one out.

## Supplemental columns

Columns that `schema-map`'s matcher sets aside as a coarser grouping
(AFG's `regioncode`, BFA's `adm1_pcode_old`, CPV's `island`) are reported
as `supplemental-column` warnings. They are legitimate data, but
`name-detect` and `code-detect` refuse such a layer without explicit
`--name-field`/`--code-field`, so the warning says so.

## Real-data results

Run structurally on every latest original admin1 to admin5 layer in the
portolan catalog (281 layers): 36 rows. 26 are `supplemental-column` (14
layers). The other 10 are all real: two adm4 codes under two adm3 codes
each in MMR admin4 (7 rows), BGR's `adm0_bg`/`adm1_bg` with no `adm2_bg`,
and ZAF's `adm1_id` to `adm3_id` with no `adm0_id` or `adm4_id`.
