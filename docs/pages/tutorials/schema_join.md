---
title: "schema-join"
---

Copies a parent layer's admin-hierarchy columns onto each child it
overlaps most, leaving geometry untouched. A column the child already
carries with different values is kept as-is, with the parent's values
added alongside it as a numbered sibling (`adm2_name1`). Every child with
no parent, a weak best match, or a differing value gets a row in an
`_issues` file.

## Example 1: basic run, structural auto-detection, output name chosen automatically

    topo-tools schema-join admin3.parquet admin2.parquet

## Example 2: chain levels coarsest-first

    topo-tools schema-join admin2.parquet admin1.parquet admin2_join.parquet
    topo-tools schema-join admin3.parquet admin2_join.parquet admin3_join.parquet

## Example 3: custom target naming

    topo-tools schema-join admin3.parquet admin2.parquet --name-field adm{n}_name --code-field adm{n}_pcode

## Example 4: explicit issues path and a stricter overlap threshold

    topo-tools schema-join admin3.gpkg admin2.gpkg admin3_join.gpkg --issues-output review.gpkg --min-overlap 0.9
