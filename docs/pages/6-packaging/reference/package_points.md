---
title: "package-points"
description: "Make one label point for each admin unit, at every level, in one file."
sidebar:
  order: 5
---

Make one label point for each admin unit, at every level, in one file.

## Synopsis

```text
topo-tools package-points [OPTIONS] INPUT_FILE [OUTPUT_FILE]
```

## Description

Each point is the spot inside the unit farthest from its edges, so it always falls inside the unit, unlike a centroid. OUTPUT_FILE defaults to INPUT_FILE with a "_points" suffix.

## Options

- `--name-field TEXT`: Name column of each level, with {n} for the level number, e.g. 'adm{n}_name'. Give it with `--code-field`. Without both, levels are detected from the data.
- `--code-field TEXT`: Code column of each level, with {n} for the level number, e.g. 'adm{n}_code'. Give it with `--name-field`. Without both, levels are detected from the data.
- `--depth-column TEXT`: Name of the added column holding each point's admin level. [default: adm_lvl]
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|points|outputs]`: Run only this step of the tool, for debugging.

## Examples

```sh
topo-tools package-points admin3.geojson
```
