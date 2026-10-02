---
title: "name-clean"
sidebar:
  order: 4
  badge:
    text: Draft
    variant: caution
---

## Checks

- `name-clean` MUST run `name-detect`'s inputs, levels and checks stages
  unchanged, with the same `name_field`/`code_field` rules.

## Fixes

- `name-clean` MUST fix only units reported as `whitespace`,
  `invisible-character`, `unnormalized-unicode`, or `encoding-artifact` with
  a `suggested` value, rewriting that name column as `name_clean(name)`, so
  a name with several safe defects is fixed in one pass.
- It MUST NOT change a name whose fixed value would be empty, and MUST NOT
  change case, spelling, duplicates, codes or geometry.

## Outputs

- The cleaned layer MUST hold every input row, in the input's format.
- The issues report MUST be `name-detect`'s report plus a `fixed` column:
  true for a row whose finding was fixed, false for a row left for review.
  It MUST always be written, even with zero rows.

## Configuration (`api.name_clean.clean()` / CLI)

- `output_path` MUST default to the input path with a `_cleaned` stem
  suffix; `issues_path` MUST default as in `name-detect`, ending in `.csv`
  or `.parquet`, raising `ValueError` otherwise.
- `name-clean` MUST raise `FileExistsError` if either output already exists
  and overwriting wasn't requested.
- `step`, if given, MUST be one of `inputs`, `levels`, `checks`, `fix`,
  `outputs`; any other value MUST raise `ValueError`.

## Examples

### Example 1: basic run, output and CSV report named automatically

    topo-tools name-clean admin3.parquet

### Example 2: explicit level columns and output names

    topo-tools name-clean admin3.parquet admin3_clean.parquet \
      admin3_name_issues.csv --name-field adm{n}_name --code-field adm{n}_code
