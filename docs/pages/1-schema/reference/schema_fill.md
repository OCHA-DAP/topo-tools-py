---
title: "schema-fill"
description: "Fill each row's empty finer admin columns from its coarser ones."
sidebar:
  order: 6
---

Fill each row's empty finer admin columns from its coarser ones.

## Synopsis

```text
topo-tools schema-fill [OPTIONS] INPUT_FILE [OUTPUT_FILE]
```

## Description

A row for an admin2 unit in an admin4 file gets its admin2 code and name copied into the admin3 and admin4 columns. A column for the row's own admin level ("adm_lvl") is added first, so filled rows can be told apart. A missing value at a row's own level is left empty.

## Options

- `--name-field TEXT`: Name column of each level, with {n} for the level number, e.g. 'adm{n}_name'. Give it with `--code-field`. Without both, levels are detected from the data.
- `--code-field TEXT`: Code column of each level, with {n} for the level number, e.g. 'adm{n}_code'. Give it with `--name-field`. Without both, levels are detected from the data.
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|fill|outputs]`: Run only this step of the tool, for debugging.
- `--depth-column TEXT`: Name of the added column holding each row's own admin level, taken before filling. [default: adm_lvl]

## Examples

Basic run, levels detected from the data:

```sh
topo-tools schema-fill admin4.geojson
```
