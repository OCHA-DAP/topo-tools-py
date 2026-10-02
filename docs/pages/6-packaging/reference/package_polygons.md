---
title: "package-polygons"
description: "Merge a polygon layer into one layer for each coarser admin level."
sidebar:
  order: 4
---

Merge a polygon layer into one layer for each coarser admin level.

## Synopsis

```text
topo-tools package-polygons [OPTIONS] INPUT_FILE [OUTPUT_FILE]
```

## Description

Units are dissolved by their code at every admin level found in the file. OUTPUT_FILE must contain "{n}", replaced by each level number. Without it, each level is written to INPUT_FILE with an "_admin{n}" suffix. The finest level is skipped when its path would be INPUT_FILE itself.

## Options

- `--issues-file TEXT`: Path for the issues report of each level. It must contain "{n}", replaced by each level number. Defaults to each level's output with an "_issues" suffix.
- `--name-field TEXT`: Name column of each level, with {n} for the level number, e.g. 'adm{n}_name'. Give it with `--code-field`. Without both, levels are detected from the data.
- `--code-field TEXT`: Code column of each level, with {n} for the level number, e.g. 'adm{n}_code'. Give it with `--name-field`. Without both, levels are detected from the data.
- `--output-name-field TEXT`: Rename the `--name-field` columns to this pattern in every output, e.g. 'adm{n}_label'. Needs `--name-field` and `--code-field`.
- `--output-code-field TEXT`: Rename the `--code-field` columns to this pattern in every output, e.g. 'adm{n}_pcode'. Needs `--name-field` and `--code-field`.
- `--aggregation TEXT`: How to combine a column whose values differ inside one unit, as 'column=function', where function is sum, min, max, avg or first. By default numbers are summed and other columns dropped. Repeat for more columns.
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|dissolve|outputs]`: Run only this step of the tool, for debugging.

## Examples

Default naming: input_admin1.geojson, input_admin2.geojson, ...:

```sh
  topo-tools package-polygons admin3.geojson
```

Choose the output names and the level columns:

```sh
topo-tools package-polygons admin3.geojson "level_{n}.geojson" \
  --name-field adm{n}_name --code-field adm{n}_pcode
```
