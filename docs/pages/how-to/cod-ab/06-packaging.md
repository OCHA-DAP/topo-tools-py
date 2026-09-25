---
status: draft
title: "6. Packaging"
---

Last step of COD-AB
cleaning. Run `package` against
the coded output of step 4, with step 5's name fixes applied.

    topo-tools package admin2_coded.parquet --output "release/{x}.parquet" \
      --name-field "adm{n}_name" --code-field "adm{n}_code" \
      --output-code-field "adm{n}_pcode"

Earlier steps work with `adm{n}_code`; `--output-code-field` writes the
release's code columns as `adm{n}_pcode`.

Writes one `release/admin{n}.parquet` per detected level,
`release/points.parquet` (one label point per admin unit), and
`release/lines.parquet` (the deduplicated boundary network).

`topo-clean`, `edge-match`, and `code-refactor` each write an issues file
only when they find something to report; load one as a map layer, not
just a table, to see exactly which features it touched.
