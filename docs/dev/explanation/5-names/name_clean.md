---
title: "name-clean"
sidebar:
  order: 7
  badge:
    text: Draft
    variant: caution
---

`name-clean` runs `name-detect`'s stages, then applies only the fixes that
can't change a name's meaning, the ones `name-detect` already gives as
`suggested`. Case, typos and duplicates are left for review, since no rule
can tell which spelling is right.

| Stage | Table | What it does |
| --- | --- | --- |
| `_01_inputs` to `_03_checks` | `{name}_01` to `{name}_03` | `name-detect`'s stages |
| `_04_fix` | `{name}_01` | rewrites each flagged unit's name as `name_clean(name)` |
| outputs | | exports the cleaned layer, then `name-detect`'s report with `fixed` |

On the FAO GAUL admin2 layer (43,803 rows) it fixes 56 spacing and 9 NFC
rows; running `name-detect` on the output reports only the 8 rows left for
review.
