---
title: "6. Package for output"
---

Last step of [preparing an administrative boundary
release](./). Run `package` directly
against the coded output of [step 3](03-assign-codes/), not the
schema-filled output of step 5: `package-points`/`package-lines` each
stamp their own depth column and would collide with an existing `adm_lvl`
(see `docs/pages/reference/package.md`).

    topo-tools package district_coded.parquet --output "release/{x}.parquet"

Writes `release/admin0.parquet`, `release/admin1.parquet`,
`release/points.parquet` (one label point per admin unit, 2 provinces + 8
districts), and `release/lines.parquet` (the deduplicated boundary
network).

`topo-clean`, `edge-match`, and `code-refactor` each write an issues file
only when they find something to report; load one as a map layer, not
just a table, to see exactly which features it touched.
