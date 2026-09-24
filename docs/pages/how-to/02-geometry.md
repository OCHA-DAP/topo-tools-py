---
title: "2. Clean geometry"
---

Second step of [preparing an administrative boundary
release](administrative-boundary-release/).

Use `topo-detect` first, without `--maximum-gap-width`, to inspect your
dataset's own gap/overlap distribution before deciding on a setting, then
fix what's found:

    topo-tools topo-clean admin2_mapped.parquet admin2_topo.parquet \
      --issues-file admin2_topo_issues.parquet --maximum-gap-width all

Load the issues file as a map layer, not just a table, to see exactly
which features got fixed (`kind='gap'`/`kind='overlap'`, `fixed=true`).

## Fitting a finer level into one parent unit (uncommon)

Skip this unless a source authority also provides a level finer than your
base level, covering only part of it. Isolate the target parent unit
first, then fit the finer layer to it in one pass (match by overlap,
extend to fill any gap, clip to the parent). No codes exist yet at this
stage, so filter by name rather than p-code:

    duckdb -c "INSTALL spatial; LOAD spatial;
      COPY (SELECT * FROM 'admin2_topo.parquet' WHERE adm2_name = 'your_district')
      TO 'parent.parquet';"

    topo-tools edge-match finer_level_raw.parquet parent.parquet \
      finer_matched.parquet --issues-file finer_matched_issues.parquet

Check the issues file (if written) for anything that didn't match or
clip cleanly.

## Checking that every level still dissolves cleanly

Confirm the geometry is complete enough to derive every ancestor level
before moving on to coding. `package-polygons`'s structural auto-detection
relies on a nested p-code format to tell levels apart, which doesn't exist
yet at this stage, so pass `--name-field`/`--code-field` explicitly:

    topo-tools schema-fill admin2_topo.parquet admin2_filled.parquet
    topo-tools package-polygons admin2_filled.parquet \
      admin2_filled_admin{n}.parquet \
      --name-field "adm{n}_name" --code-field "adm{n}_code"

This is a check, not the final output: it writes one dissolved file per
ancestor level so you can confirm they look right, but the actual release
packaging (step 5) re-derives everything from the coded data.

If the source supplied its own higher-level files, compare each dissolved
level against its supplied counterpart with `change`. A unit reported as
anything other than `unchanged`/`renamed` means the base level's declared
parent attributes disagree with the supplied higher-level shapes. Resolve
that with the data provider before coding.

Next: [assign hierarchical codes](03-codes/).
