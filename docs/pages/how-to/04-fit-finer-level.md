---
title: "4. Fit a finer level into one district (uncommon)"
---

Optional step of [preparing an administrative boundary
release](administrative-boundary-release/). Skip this unless a source
authority also provides a level finer than your base level. Continues from
the coded output of [step 3](03-assign-codes/), plus a second
fixture:

<https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/tests/fixtures/how_to_neighborhood_raw.parquet>

Two neighborhoods covering only part of one district (a deliberate wedge
missing).

Isolate the target parent district first, then fit the finer layer to it
in one pass (match by overlap, extend to fill any gap, clip to the
parent):

    duckdb -c "INSTALL spatial; LOAD spatial;
      COPY (SELECT * FROM 'district_coded.parquet' WHERE adm1_code = 'TT.02.04')
      TO 'riverside_parent.parquet';"

    topo-tools edge-match how_to_neighborhood_raw.parquet riverside_parent.parquet \
      neighborhood_matched.parquet --issues-file neighborhood_matched_issues.parquet

The fixture's two neighborhoods cover only part of district `TT.02.04`
(Riverside); after this step their union covers it exactly, with no issues
file written (nothing to report).

Next: [derive ancestor levels and fill hierarchy
attributes](05-fill-and-derive-ancestors/).
