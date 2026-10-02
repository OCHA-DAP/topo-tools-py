---
title: "validate"
description: "Check one layer with every detect tool and summarize the results."
sidebar:
  order: 7
---

Check one layer with every detect tool and summarize the results.

## Synopsis

```text
topo-tools validate [OPTIONS] INPUT_FILE
```

## Description

Runs schema-detect, topo-detect, code-detect and name-detect on INPUT_FILE, each writing its own report, then writes a summary with one row per stage and kind. A stage that fails is recorded in the summary and the others still run; code-detect and name-detect are skipped when schema-detect cannot detect the levels. Exits with status 1 when any report has an error or a stage fails; warnings alone exit 0.

## Options

- `--output-dir TEXT`: Folder for the reports and the summary (default: beside INPUT_FILE).
- `--name-field TEXT`: Name column of each level, with {n} for the level number, e.g. 'adm{n}_name'. Give it with `--code-field`. Without both, levels are detected from the data.
- `--code-field TEXT`: Code column of each level, with {n} for the level number, e.g. 'adm{n}_code'. Give it with `--name-field`. Without both, levels are detected from the data.
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).

## Examples

Reports and summary beside the input:

```sh
topo-tools validate admin3.parquet
```

Reports in their own folder, explicit level columns:

```sh
topo-tools validate admin3.parquet --output-dir checks \
  --name-field adm{n}_name --code-field adm{n}_pcode
```
