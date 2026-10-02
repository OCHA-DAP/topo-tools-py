---
title: "code-detect"
sidebar:
  order: 8
  badge:
    text: Draft
    variant: caution
---

`code-detect` checks one coded layer's unit codes, without changing it.
Every check is DuckDB SQL over a table of level codes, so the same queries
run in DuckDB-WASM.

## Stages

| Stage | Table | What it does |
| --- | --- | --- |
| `_01_inputs` | `{name}_01` | reads and reprojects the input |
| `_02_levels` | `{name}_02` | one row per distinct code, parent code and name per level, with its feature count |
| `_03_checks` | `{name}_03` | one SQL query per kind (`{name}_03_tmp{n}`), unioned |
| `_04_outputs` | `{name}_04` | keys and severity; writes CSV or Parquet |

## Code shape instead of a parsed format

`format-outlier` and `prefix-mismatch` compare codes by shape (every
letter as `A`, every digit as `9`) and by `starts_with`, not by
`core.code`'s format detection. `detect_code_format()` infers one root,
delimiter and width per level to generate new codes; a check only needs
to know which codes differ from the rest of their level, and a shape
answers that for any coding scheme, including ones `core.code` can't
parse. Both checks report only where at least 90% of a level's codes
follow the rule, so a level coded in two schemes reads as
`format-undetected` rather than as half its codes being wrong.

## Duplicates

`duplicate-code` counts features, not units: a code on two features is
reported even when both carry the same name and parent, which is how one
unit split into separate features (instead of one MultiPolygon) shows up.
Codes repeated across parents at a coarser level are `schema-detect`'s
`multiple-parents`.

## Real-data results

Run structurally on every latest original admin1 to admin5 layer in the
portolan catalog (281 layers), 264 were checked and 17 refused by level
resolution (supplemental columns, or levels not detected). 141 rows in 6
layers, all real:

- COL admin3: 36 duplicated codes (each one unit split across features),
  44 codes one digit short, and `COPUERTO LOPEZ` as a code; 3 codes don't
  start with their parent's code.
- UGA admin3: 4 codes each split across features.
- MMR admin2 to admin4: 5 self-administered zone codes (`MMR005S001`)
  shaped unlike the level, as warnings; in admin4 also 22 codes not
  starting with their parent's code (7 of them the codes `schema-detect`
  reports under two parents), 8 duplicated, 6 units with no code.
- SOM admin2: one `Unspecified` code.
