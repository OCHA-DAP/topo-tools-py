---
title: "2. Fix internal topology"
---

Second step of [preparing an administrative boundary
release](administrative-boundary-release/). Continues from the mapped
output of [step 1](01-map-schema/).

    topo-tools topo-clean district_mapped.parquet district_topo.parquet \
      --issues-file district_topo_issues.parquet --maximum-gap-width all

The fixture has one enclosed gap and one 0.05-unit overlap; both get fixed,
and `district_topo_issues.parquet` records them (`kind='gap'`,
`kind='overlap'`, both `fixed=true`). Use `topo-detect` first, without
`--maximum-gap-width`, to inspect a real dataset's own gap/overlap
distribution before deciding that setting.

Next: [assign hierarchical codes](03-assign-codes/).
