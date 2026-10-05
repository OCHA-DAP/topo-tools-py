---
title: "code-detect"
sidebar:
  order: 3
  badge:
    text: Draft
    variant: caution
---

## Inputs

- `code-detect` MUST read the one input and reproject it to EPSG:4326 via
  `core.io.read_and_reproject()`, columns untouched. It takes the coded
  finest-level layer, hierarchy embedded as columns.

## Level resolution

- Levels MUST come from `core.schema_map.resolve_levels()`, the same
  resolution `name-detect` uses: an explicit `name_field`/`code_field` pair
  (given together or not at all), or structural detection otherwise,
  raising `ValueError` when levels can't be resolved reliably.
- A level without a name column MUST still have its codes checked.
- A level's parent is the next coarser resolved level's code.

## Checks

- `code-detect` MUST report each of these kinds:

  | kind | severity | finding |
  | --- | --- | --- |
  | `blank-code` | error | a unit with no code, one row per parent |
  | `name-conflict` | error | one code with more than one name |
  | `duplicate-code` | error | a finest-level code on more than one polygon, with different names or parents |
  | `prefix-mismatch` | error | a code not starting with its parent's code, in a level where at least 90% of codes do |
  | `split-unit` | warn | a finest-level code on more than one polygon, all with the same name and parent |
  | `format-outlier` | warn | a code shaped unlike its level's most common shape, where at least 90% of the level's codes share it |
  | `format-undetected` | warn | a level whose most common code shape covers under 90% of its codes |

- A code's shape MUST be the code with every letter as `A` and every digit
  as `9`, other characters kept.
- `prefix-mismatch`, `format-outlier` and `format-undetected` MUST skip a
  level with fewer than 10 distinct codes (or code and parent pairs).
- `name-conflict` MUST be reported once per code, from the first name
  column that differs.
- If one check fails, `code-detect` MUST still report the others, and MUST
  report the failure as a `check-failed` row (severity `error`) whose
  `reason` names the check and its error.

## Outputs

- `code-detect` MUST always write the issues report, even with zero rows.
  It never modifies the input.
- Columns: `key`, `kind`, `severity`, `level`, `column`, `code_a`,
  `name_a`, `code_b`, `name_b`, `reason`. `column` is the code column, or
  the name column for `name-conflict`; `code_b` is the parent code for
  `prefix-mismatch`. A `.parquet` report MUST add `geometry` as its first
  column: the union of the units carrying `code_a`, NULL for a
  `blank-code` row. A `.csv` report MUST be UTF-8 with a BOM.

## Configuration (`api.code_detect.detect()` / CLI)

- `code-detect` MUST process exactly one input file per call.
- `issues_path` MUST default to the input path with a `_code_issues` stem
  suffix and a `.parquet` extension, and MUST end in `.csv` or `.parquet`,
  raising `ValueError` otherwise.
- `code-detect` MUST raise `FileExistsError` if `issues_path` already
  exists and overwriting wasn't requested.
- `step`, if given, MUST be one of `inputs`, `levels`, `checks`, `outputs`;
  any other value MUST raise `ValueError`.

## Examples

### Example 1: basic run, report named automatically

    topo-tools code-detect admin3.parquet

### Example 2: explicit level columns

    topo-tools code-detect admin3.parquet admin3_code_issues.csv \
      --name-field adm{n}_name --code-field adm{n}_pcode
