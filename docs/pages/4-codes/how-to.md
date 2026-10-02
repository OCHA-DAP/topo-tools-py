---
title: "Codes"
sidebar:
  order: 3
  label: "How-to"
---

Reconcile the edge-matched output of [step 3](../3-edge/how-to.md) against
the previous release, so every unit that carries over keeps its existing
code:

    topo-tools code-update admin2_previous.parquet admin2_matched.parquet \
      admin2_coded.parquet

The code format, including each level's width, is detected from the
previous release's codes, with or without a delimiter (`SN0101` or
`XYZ.001.001`). Every unit that changed gets a code above every code its
parent had in the previous release, so no code is ever issued twice.
Without a delimiter, codes in the top 10% of the range (`90`-`99` at width
2) are treated as placeholders once a parent's codes reach them, and new
codes continue below them. With codes without a delimiter (`SN0101`), a
unit matched 1:1 keeps its code even when its boundary was re-digitised
(`modified`). With a delimiter (`XYZ.001.001`), it gets a new code. Review the changelog CSV it writes:
every `split`, `merge`, `created` or `removed` unit gets a new or retired
code.

A country with no previous release starts its codes with `code-create`.
Pass `--code-field`/`--name-field` templates naming each level's columns,
and choose what happens to the source data's own codes with
`--source-codes`. Source codes are codes that came with the data and are
kept as given, whether issued by the government or agreed with the country
office.

| `--source-codes` | Admin3 code | Source code | Use for |
| --- | --- | --- | --- |
| `embed` | `XY12030045` | inside the code | country code plus source codes kept as given |
| `copy` | `XYZ.001.003.001` | kept in `adm3_code1` | sequential codes, source code alongside |
| `replace` (default) | `XYZ.001.003.001` | discarded | sequential codes only |

Source codes inside the code:

    topo-tools code-create admin3_matched.parquet admin3_coded.parquet \
      --root-code XY --delimiter '' --min-width auto --source-codes embed \
      --code-field adm{n}_code --name-field adm{n}_name

Each level's source code follows its parent's code. Codes may be
local to each level (`11`, `22`, `33`) or already include the parent's
code (`11`, `1122`, `112233`); both give `XY112233`, and existing p-codes
come out unchanged. A level with names but no code column gets sequential
numbers under its parent, sorted by name. The run stops if a row has no
source code, if a level's source codes differ in length, or if
only some of a level's codes include the parent's code.

Sequential codes, source code kept alongside:

    topo-tools code-create admin3_matched.parquet admin3_coded.parquet \
      --root-code XYZ --delimiter . --min-width 3 --source-codes copy \
      --code-field adm{n}_code --name-field adm{n}_name

Every unit gets a fresh code under its parent, sorted by its source code.
The source code is copied into the column right after it (`adm1_code` to
`adm1_code1`). IDs that aren't meant to become the codes, such as another
organisation's, are used the same way with `--delimiter ''`, giving sequential
country-code-style codes (`XY010301`), with each ID kept in its own
column.

`--min-width` sets how many digits each level's numbers are zero-padded to:

- `3`: the same width at every level.
- `2,2,4`: one width per level, coarsest first, with one entry per level.
  Under `embed`, a level that keeps its source code ignores its entry.
- `auto`: each level gets as many digits as its largest parent needs.

With a delimiter, a parent with more children than the width allows (over
99 at width 2) gets longer codes from that child on, and the issues file
lists it. Without a delimiter the run stops instead, since mixed lengths
can't be split; `auto` avoids this.

Review the result, particularly any unit whose rank could plausibly tie
with a neighbor.

Then check the coded layer's codes:

    topo-tools code-detect admin3_coded.parquet \
      --code-field adm{n}_code --name-field adm{n}_name

This writes `admin3_coded_code_issues.csv` without changing the input. Fix
every `error` row (`blank-code`, `name-conflict`, `duplicate-code`,
`prefix-mismatch`) and review each `warn` row: `split-unit` lists one
unit stored as several features, and `format-outlier`/`format-undetected`
list codes shaped unlike the rest of their level.
