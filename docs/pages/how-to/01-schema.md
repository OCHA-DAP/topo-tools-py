---
title: "1. Map the source schema"
---

First step of [preparing an administrative boundary
release](administrative-boundary-release/).

    topo-tools schema-map your_admin1.parquet crosswalk.csv

This writes `crosswalk.csv` without changing the input. `schema-map`
matches columns by cardinality (unique-value count), not by name, so open
the crosswalk and check every row before trusting it, for example:

    source_column,target_column,unique_count,note
    NAME_2,adm1_name,8,
    PCODE_2,adm1_code,8,
    LOCAL_REF,adm1_code1,8,
    NAME_1,adm0_name,2,
    PCODE_1,adm0_code,2,

A source column that happens to share a level's cardinality can match as
a decoy second code candidate (`adm1_code1` above), even when it's really
just a source reference number, not a p-code. The same trap applies to
names: `_name1`/`_name2` hold the same unit's name in another language
(`lang1`/`lang2`). A second name column whose values differ from the first
in some rows is a different name, not a translation. Keep it for
[review names](04-names/). Blank out a decoy code's `target_column` before
applying the crosswalk:

    topo-tools schema-refactor your_admin1.parquet crosswalk.csv admin1_mapped.parquet

The mapped output now has only the columns you kept a `target_column` for,
plus `geometry`.

Next: [clean geometry](02-geometry/).
