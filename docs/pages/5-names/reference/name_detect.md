---
title: "name-detect"
description: "Find problems in the unit names of one coded layer."
sidebar:
  order: 3
---

Find problems in the unit names of one coded layer.

## Synopsis

```text
topo-tools name-detect [OPTIONS] INPUT_FILE [ISSUES_FILE]
```

## Description

Checks every name column of every level: blank and placeholder names, duplicates under the same parent, encoding errors, invisible characters, spacing, case and mixed scripts. Writes the problems found without changing the layer, even when there are none. ISSUES_FILE defaults to INPUT_FILE with a "_name_issues" suffix, as CSV; a .parquet name adds each unit's geometry.

## Options

- `--name-field TEXT`: Name column of each level, with {n} for the level number, e.g. 'adm{n}_name'. Give it with `--code-field`. Without both, levels are detected from the data.
- `--code-field TEXT`: Code column of each level, with {n} for the level number, e.g. 'adm{n}_code'. Give it with `--name-field`. Without both, levels are detected from the data.
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|levels|checks|outputs]`: Run only this step of the tool, for debugging.

## Examples

Basic run, CSV report named automatically:

```sh
  topo-tools name-detect admin3.parquet
```

Explicit level columns, report with geometry:

```sh
topo-tools name-detect admin3.parquet admin3_name_issues.parquet \
  --name-field adm{n}_name --code-field adm{n}_code
```
