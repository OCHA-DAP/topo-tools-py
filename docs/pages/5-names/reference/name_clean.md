---
title: "name-clean"
description: "Fix the safe problems in the unit names of one coded layer."
sidebar:
  order: 4
---

Fix the safe problems in the unit names of one coded layer.

## Synopsis

```text
topo-tools name-clean [OPTIONS] INPUT_FILE [OUTPUT_FILE] [ISSUES_FILE]
```

## Description

Runs the same checks as name-detect, then fixes only what can't change a name's meaning: spacing, invisible characters, accents stored as separate characters, and text read with the wrong encoding when the repair is certain. Everything else stays as it is, for review. OUTPUT_FILE defaults to INPUT_FILE with a "_cleaned" suffix; ISSUES_FILE defaults to INPUT_FILE with a "_name_issues" suffix, as Parquet with each unit's geometry, with a "fixed" column marking what was fixed.

## Options

- `--name-field TEXT`: Name column of each level, with {n} for the level number, e.g. 'adm{n}_name'. Give it with `--code-field`. Without both, levels are detected from the data.
- `--code-field TEXT`: Code column of each level, with {n} for the level number, e.g. 'adm{n}_code'. Give it with `--name-field`. Without both, levels are detected from the data.
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|levels|checks|fix|outputs]`: Run only this step of the tool, for debugging.

## Examples

Basic run, output and report named automatically:

```sh
topo-tools name-clean admin3.parquet
```

Explicit level columns and output names:

```sh
topo-tools name-clean admin3.parquet admin3_clean.parquet \
  admin3_name_issues.parquet --name-field adm{n}_name --code-field adm{n}_code
```
