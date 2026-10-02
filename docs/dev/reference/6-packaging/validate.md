---
title: "validate"
sidebar:
  order: 7
  badge:
    text: Draft
    variant: caution
---

## Behavior

- `validate` MUST call `schema-detect`, `topo-detect`, `code-detect` and
  `name-detect`, in that order, through their own `api.*.detect()`
  functions against the same input, each writing its own report. It never
  modifies the input.
- `name_field`/`code_field` MUST be passed to `schema-detect`,
  `code-detect` and `name-detect`; `overwrite` is checked once up front
  and `threads`, `tmp_dir` and `debug` are passed to all four.
- If `schema-detect` reports `levels-undetected`, `validate` MUST skip
  `code-detect` and `name-detect`, recording a `skipped` row (severity
  `warn`) for each. `topo-detect` always runs.
- If a stage raises, `validate` MUST record a `failed` row (severity
  `error`, the exception message as `reason`) and still run the remaining
  stages.

## Outputs

- Reports MUST be named after the input's stem: `{stem}_schema_issues.csv`,
  `{stem}_topo_issues.parquet`, `{stem}_code_issues.csv`,
  `{stem}_name_issues.csv`, beside the input or in `output_dir`.
- The summary MUST be written to `{stem}_validate_summary.csv` (UTF-8 with
  a BOM), with columns `stage`, `kind`, `severity`, `count`, `report`,
  `reason`: one row per stage, kind and severity found, or one `count = 0`
  row with reason `no issues` for a stage whose report is empty or not
  written. Rows MUST be ordered by stage, then severity, then kind.
- `topo-detect` rows MUST take their severity from the kind: `gap` is
  `warn`, `overlap` and `micro-polygon` are `error`.
- `validate` MUST log the summary table.

## Configuration (`api.validate.validate()` / CLI)

- `validate` MUST process exactly one input file per call.
- `validate` MUST raise `FileExistsError` before running any stage if any
  report or the summary already exists and overwriting wasn't requested.
- `validate()` MUST return `True` if any summary row has severity `error`,
  `False` otherwise. The CLI MUST exit with status 1 when it returns
  `True`, and 0 otherwise.
- `validate` MUST NOT expose `--step` or per-stage report paths.

## Examples

### Example 1: reports and summary beside the input

    topo-tools validate admin3.parquet

### Example 2: reports in their own folder, explicit level columns

    topo-tools validate admin3.parquet --output-dir checks \
      --name-field adm{n}_name --code-field adm{n}_pcode
