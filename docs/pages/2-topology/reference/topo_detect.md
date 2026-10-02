---
title: "topo-detect"
description: "Find gaps and overlaps between the polygons of one layer."
sidebar:
  order: 3
---

Find gaps and overlaps between the polygons of one layer.

## Synopsis

```text
topo-tools topo-detect [OPTIONS] INPUT_FILE [OUTPUT_FILE]
```

## Description

Writes the problems found without changing the layer. OUTPUT_FILE defaults to INPUT_FILE with an "_issues" suffix.

## Options

- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|issues|outputs]`: Run only this step of the tool, for debugging.

## Examples

Basic run, output name chosen automatically:

```sh
  topo-tools topo-detect example.geojson
```

Explicit output:

```sh
topo-tools topo-detect example.gpkg example_issues.gpkg
```
