---
title: "5. Package for output"
---

Last step of [preparing an administrative boundary
release](administrative-boundary-release/). Run `package` directly
against the coded output of step 3, not step 2's dissolve-completeness
check: `package-points`/`package-lines` each stamp their own depth column
and would collide with an existing `adm_lvl` (see
`docs/pages/reference/package.md`).

    topo-tools package admin1_coded.parquet --output "release/{x}.parquet"

Writes one `release/admin{n}.parquet` per detected level,
`release/points.parquet` (one label point per admin unit), and
`release/lines.parquet` (the deduplicated boundary network).

`topo-clean`, `edge-match`, and `code-refactor` each write an issues file
only when they find something to report; load one as a map layer, not
just a table, to see exactly which features it touched.
