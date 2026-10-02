---
title: "schema-join"
description: "Copy admin columns from a join layer onto the input features they overlap."
sidebar:
  order: 5
---

Copy admin columns from a join layer onto the input features they overlap.

## Synopsis

```text
topo-tools schema-join [OPTIONS] INPUT_FILE JOIN_FILE [OUTPUT_FILE]
```

## Description

Each input feature takes the columns of the join feature it overlaps most. Geometry is not changed. When a column already has a different value, both are kept: the join layer's value goes in a new numbered column (adm2_name1).

## Options

- `--issues-output TEXT`: Path for the issues report. Defaults to OUTPUT_FILE with an "_issues" suffix.
- `--name-field TEXT`: Name column of each level, with {n} for the level number, e.g. 'adm{n}_name'. Give it with `--code-field`. Without both, levels are detected from the data.
- `--code-field TEXT`: Code column of each level, with {n} for the level number, e.g. 'adm{n}_code'. Give it with `--name-field`. Without both, levels are detected from the data.
- `--min-overlap FLOAT`: Report an input feature when its best-matching join feature covers less than this share of its area. [default: 0.5]
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|assign|join|outputs]`: Run only this step of the tool, for debugging.

## Examples

Copy admin2 columns onto an admin3 layer:

```sh
  topo-tools schema-join admin3.geojson admin2.geojson
```

Build up a full hierarchy one level at a time, coarsest first:

```sh
topo-tools schema-join admin2.parquet admin1.parquet admin2_join.parquet
topo-tools schema-join admin3.parquet admin2_join.parquet admin3_join.parquet
```
