---
title: "1. Map the source schema"
---

First step of [preparing an administrative boundary
release](administrative-boundary-release/).

Run `schema-map` on each supplied level:

    topo-tools schema-map admin2.parquet admin2_crosswalk.csv

This writes a crosswalk without changing the input. `schema-map` matches
columns by their values, not their names, so check every row:

    source_column, target_column, unique_count, note
    NAME_2,        adm2_name,     8,
    PCODE_2,       adm2_code,     8,
    NAME_1,        adm1_name,     2,
    PCODE_1,       adm1_code,     2,

A column with the same number of unique values as a level can be matched
by mistake, such as a reference number mapped as a second code
(`adm2_code1`). Blank out its `target_column`. Map extra name columns (a
translation or alternate spelling) to the next free `adm2_name1`,
`adm2_name2`, and never use a target outside the `adm{n}_code`/`adm{n}_name`
families. Then apply it:

    topo-tools schema-refactor admin2.parquet admin2_crosswalk.csv admin2_mapped.parquet

The output keeps only the columns with a `target_column`, plus `geometry`.

With more than one level, copy each parent's codes and names onto its
children, coarsest first, overwriting each child in place:

    topo-tools schema-join admin2_mapped.parquet admin1_mapped.parquet admin2_mapped.parquet

If any child's value differs from its parent's, `schema-join` keeps the
child's column and adds the parent's as the next free sibling
(`adm2_name1`), filled on every row. Its issues file lists:

- `value-mismatch`: a differing name or code, settled in
  [review names](04-names/);
- `no-parent`, `low-overlap`: a child outside or mostly outside its
  parent, settled with the data provider before coding.
