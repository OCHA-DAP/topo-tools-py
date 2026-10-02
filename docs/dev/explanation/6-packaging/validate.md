---
title: "validate"
sidebar:
  order: 12
  badge:
    text: Draft
    variant: caution
---

`validate` runs every detect tool that needs only one layer and
summarizes their reports, as a check before packaging. It composes at the
`api.*()` layer, like `package`: each detect reads the input on its own
connection, so a stage that raises leaves the others unaffected. Edge
checks need an overlay layer and have no place in a single-layer check.

## Stages

| Stage | Tool | Report |
| --- | --- | --- |
| schema | `schema-detect` | `{stem}_schema_issues.csv` |
| topo | `topo-detect` | `{stem}_topo_issues.parquet` |
| code | `code-detect` | `{stem}_code_issues.csv` |
| name | `name-detect` | `{stem}_name_issues.csv` |

`code-detect` and `name-detect` need the admin levels resolved, so
`validate` skips them when `schema-detect` reports `levels-undetected`.
`schema-detect` runs the same level resolution they do, so a layer they
would refuse is reported there once, with the reason, and a `failed` row
means a stage broke for another reason.

## Summary

The summary is built in an in-memory DuckDB table from the written
reports, one `GROUP BY` per report. `topo-detect`'s report has no
severity column, so `validate` assigns one per kind: an overlap or a
micro-polygon is an error, but a gap is a warning, since a gap may be a
real hole in the layer (a lake, an enclave).

## Usage

```sh
topo-tools validate admin3.parquet
```

```python
from topo_tools import validate

has_errors = validate("admin3.parquet", "checks")
```
