---
title: "name-detect"
sidebar:
  order: 6
  badge:
    text: Draft
    variant: caution
---

`name-detect` lists name defects in a coded admin layer without changing it.
Every check is rule-based DuckDB SQL using built-in functions, so the same
queries run in DuckDB-WASM and no AI is needed to filter the report. The
checks favour precision over recall: a check that mostly flags legitimate
names is left out (digits-only names, stray punctuation, near-duplicate
spellings without a second signal), and each check skips the cases where its
rule breaks: accents distinguish names in Vietnamese and vowel signs in
Brahmic scripts, Georgian is stored as lower case, acronyms are capitals,
and NFC reorders Myanmar marks without composing anything.

## Stages

| Stage | Table | What it does |
| --- | --- | --- |
| `_01_inputs` | `{name}_01` | reads and reprojects the input |
| `_02_levels` | `{name}_02` | one row per level, name column, code, parent code and name |
| `_03_checks` | `{name}_03` | one SQL query per kind (`{name}_03_tmp{n}`), unioned |
| `_04_outputs` | `{name}_04` | column rollup, blank-row merge, keys, severity; writes CSV or Parquet |

`_03_checks` creates two macros (`core/name_detect/_macros.py`):
`name_repair_mojibake(s)` re-encodes a name as cp1252 through a fixed byte
table and decodes it as UTF-8, and `name_clean(s)` composes every safe fix
(mojibake repair, standard spaces, invisible characters removed, NFC,
trimmed and collapsed spaces). `suggested` comes from these.

## Real-data results

Run on the finest level of every country in the portolan catalog (112
countries, explicit `adm{n}_name`/`adm{n}_pcode`): about 820 rows, mostly
missing names (KGZ, LKA, LBN), same-named units under one parent (COL, UKR,
EGY, real places but still ambiguous for users), one code carrying 17 ward
names (MMR), units with no code (MMR) and mojibake (COL). BHR stage 4
reports one row, `KING FAHAD CAUSWAY`. The global OCHA, FAO and SALB layers
(up to 216k rows) run in under 25 seconds at about 3 GB peak memory; a
layer holding several countries and no level 0 code column reports
same-named units in different countries as duplicates.
