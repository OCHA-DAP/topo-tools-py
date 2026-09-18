---
title: "5. Fill attributes and derive ancestor levels"
---

Fifth step of [preparing an administrative boundary
release](administrative-boundary-release/). Continues from the coded
output of [step 3](03-assign-codes/).

    topo-tools schema-fill district_coded.parquet district_filled.parquet
    topo-tools package-polygons district_filled.parquet

Writes `district_filled_admin0.parquet` (the 2 provinces, dissolved) and
`district_filled_admin1.parquet`, alongside the depth-stamped
`district_filled.parquet` itself.

Next: [package the full cartographic bundle](06-package-for-output/).
