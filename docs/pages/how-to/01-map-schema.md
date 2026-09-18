---
title: "1. Map the source schema"
---

First step of [preparing an administrative boundary
release](administrative-boundary-release/). Every command in this series
runs as written against a small synthetic fixture committed to this repo:

<https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/tests/fixtures/how_to_district_raw.parquet>

8 districts across 2 provinces, deliberately messy: non-spec column names,
one gap, one overlap, no real codes yet.

    topo-tools schema-map how_to_district_raw.parquet crosswalk.csv

This writes `crosswalk.csv` without changing the input. `schema-map`
matches columns by cardinality (unique-value count), not by name, so open
the crosswalk and check every row before trusting it:

    source_column,target_column,unique_count,note
    NAME_2,adm1_name,8,
    PCODE_2,adm1_code,8,
    LOCAL_REF,adm1_code1,8,
    NAME_1,adm0_name,2,
    PCODE_1,adm0_code,2,

`LOCAL_REF` is a source reference code that happens to have one distinct
value per district, the same cardinality as the real `PCODE_2` code
column, so it matched as a second code candidate (`adm1_code1`). Blank out
its `target_column` before applying the crosswalk:

    topo-tools schema-refactor how_to_district_raw.parquet crosswalk.csv district_mapped.parquet

The mapped output now has just `adm0_name`, `adm0_code`, `adm1_name`,
`adm1_code`, and `geometry`.

Next: [fix internal topology](02-fix-topology/).
