---
title: "package"
description: "Run package-polygons, package-points and package-lines on one input."
sidebar:
  order: 3
---

Run package-polygons, package-points and package-lines on one input.

## Synopsis

```text
topo-tools package [OPTIONS] INPUT_FILE
```

## Options

- `--output TEXT`: Output path containing "{x}", replaced by "admin{n}", "points" or "lines" for each output. Without it, each tool's default name is used.
- `--name-field TEXT`: Name column of each level, with {n} for the level number, e.g. 'adm{n}_name'. Give it with `--code-field`. Without both, levels are detected from the data.
- `--code-field TEXT`: Code column of each level, with {n} for the level number, e.g. 'adm{n}_code'. Give it with `--name-field`. Without both, levels are detected from the data.
- `--output-name-field TEXT`: Rename the `--name-field` columns to this pattern in every output, e.g. 'adm{n}_label'. Needs `--name-field` and `--code-field`.
- `--output-code-field TEXT`: Rename the `--code-field` columns to this pattern in every output, e.g. 'adm{n}_pcode'. Needs `--name-field` and `--code-field`.
- `--aggregation TEXT`: How package-polygons combines a column whose values differ inside one unit, as 'column=function', where function is sum, min, max, avg or first. By default numbers are summed and other columns dropped. Repeat for more columns.
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).

## Examples

Defaults for all three outputs:

```sh
  topo-tools package admin3.geojson
```

Choose where the outputs go:

```sh
topo-tools package admin3.geojson --output "web/{x}.geojson"
```
