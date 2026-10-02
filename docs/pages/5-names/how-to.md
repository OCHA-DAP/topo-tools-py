---
title: "Names"
sidebar:
  order: 2
  label: "How-to"
---

Continues from the coded output of [step 4](../4-codes/how-to.md). Fix the
safe name problems and list the rest:

    topo-tools name-clean admin3_coded.parquet admin3_names.parquet \
      admin3_name_fixes.csv --name-field adm{n}_name --code-field adm{n}_code

This fixes spacing, invisible characters, accents stored as separate
characters, and text read with the wrong encoding when the repair is
certain, marking those rows `fixed`. Keep this file: it records what
`name-clean` changed. Open the CSV in a spreadsheet and
filter out the fixed rows. Each row names the unit by its code (`code_a`,
and `code_b` for a pair). Fix every `error` row and review each `warn` row.
A row with no code covers a whole column.

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

Write the fixed names back to the cleaned file, for example in DuckDB (one
`WHEN` per unit):

    COPY (
      SELECT * REPLACE (
        CASE adm3_code WHEN 'XY020301' THEN 'Example Name' ELSE adm3_name END
        AS adm3_name)
      FROM 'admin3_names.parquet'
    ) TO 'admin3_names_edited.parquet' (FORMAT PARQUET, GEOPARQUET_VERSION 'V2');

Then check the edited file with `name-detect`, which runs the same checks
without changing anything:

    topo-tools name-detect admin3_names_edited.parquet admin3_name_issues.csv \
      --name-field adm{n}_name --code-field adm{n}_code

Repeat until no `error` row is left. Keep the last issues file: it's this
step's record, written even when empty.
