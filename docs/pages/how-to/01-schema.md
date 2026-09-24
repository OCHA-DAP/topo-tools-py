---
title: "1. Map the source schema"
---

First step of [preparing an administrative boundary
release](administrative-boundary-release/).

    topo-tools schema-map your_admin2.parquet crosswalk.csv

This writes `crosswalk.csv` without changing the input. `schema-map`
matches columns by cardinality (unique-value count), not by name, so open
the crosswalk and check every row before trusting it, for example:

    source_column, target_column, unique_count, note
    NAME_2,        adm2_name,     8,
    PCODE_2,       adm2_code,     8,
    LOCAL_REF,     adm2_code1,    8,
    NAME_1,        adm1_name,     2,
    PCODE_1,       adm1_code,     2,

A source column that happens to share a level's cardinality can match as
a decoy second code candidate (`adm2_code1` above), even when it's really
just a source reference number, not a p-code. The same trap applies to
names. Map every name column for a level to that level's name family: the
primary name to `adm2_name`, and any other (a translation, an alternate
spelling, or a second name that differs from the first) to the next free
`adm2_name1`, `adm2_name2`. Never give a column a target outside the
`adm{n}_code`/`adm{n}_name` families. Blank out a decoy code's
`target_column` before applying the crosswalk:

    topo-tools schema-refactor your_admin2.parquet crosswalk.csv admin2_mapped.parquet

The mapped output now has only the columns you kept a `target_column` for,
plus `geometry`.

With more than one level, copy each parent's codes and names onto its
children, coarsest first, overwriting each child in place:

    topo-tools schema-join admin2_mapped.parquet admin1_mapped.parquet admin2_mapped.parquet
    topo-tools schema-join admin3_mapped.parquet admin2_mapped.parquet admin3_mapped.parquet

Where a child's own value differs from its parent's, `schema-join` keeps
both, adding the parent's as the next free numbered sibling
(`adm2_name1`), and writes one issues row per child for
[review names](04-names/).

Next: [clean geometry](02-geometry/).
