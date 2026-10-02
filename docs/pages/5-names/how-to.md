---
title: "Names"
sidebar:
  order: 2
  label: "How-to"
---

Continues from the coded output of [step 4](../4-codes/how-to.md). List
the name problems:

    topo-tools name-detect admin3_coded.parquet admin3_name_issues.csv \
      --name-field adm{n}_name --code-field adm{n}_code

Open the CSV in a spreadsheet. Each row names the unit by its code
(`code_a`, and `code_b` for a pair). Fix every `error` row. Review each
`warn` row; where `suggested` holds a value, it's the safe fix (spacing,
invisible characters, accents stored as separate characters, or text
read with the wrong encoding). A row with no code covers a whole column.

Also check, against the reference release, each unit whose code already
existed in `{ref_version}`: a real administrative rename is expected, a
diverging spelling of the same unit isn't.

For each `value-mismatch` row in stage 1's issues file, a child's own
`adm{N}_name` differs from its join layer's, which `schema-join` added as
`adm{N}_name{k}`. Pick one spelling per parent unit and write it to
`adm{N}_name` on every child under it. Drop that `schema-join` sibling only
once no row still differs from `adm{N}_name`. Keep any `adm{N}_name{k}`
mapped from the source in stage 1, since it's an alternate name, not a
conflict.

Write the fixed names back to the coded file, then run `name-detect` again
until no `error` row is left. Keep the last issues file: it's this step's
record, written even when empty.
