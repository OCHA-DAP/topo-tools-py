---
title: "package-lines"
description: "Make one line layer of admin boundaries, each line drawn once."
sidebar:
  order: 6
---

Make one line layer of admin boundaries, each line drawn once.

## Synopsis

```text
topo-tools package-lines [OPTIONS] INPUT_FILE [OUTPUT_FILE]
```

## Description

Lines between two units and along the outer edge are included, each tagged with the coarsest admin level it belongs to. OUTPUT_FILE defaults to INPUT_FILE with a "_lines" suffix.

## Options

- `--name-field TEXT`: Name column of each level, with {n} for the level number, e.g. 'adm{n}_name'. Give it with `--code-field`. Without both, levels are detected from the data.
- `--code-field TEXT`: Code column of each level, with {n} for the level number, e.g. 'adm{n}_code'. Give it with `--name-field`. Without both, levels are detected from the data.
- `--depth-column TEXT`: Name of the added column holding the coarsest admin level each boundary line belongs to. [default: adm_lvl]
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|boundaries|outputs]`: Run only this step of the tool, for debugging.

## Examples

```sh
topo-tools package-lines admin3.geojson
```
