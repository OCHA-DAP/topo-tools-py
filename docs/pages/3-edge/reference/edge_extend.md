---
title: "edge-extend"
description: "Extend polygons outward to fill the gaps around and between them."
sidebar:
  order: 3
---

Extend polygons outward to fill the gaps around and between them.

## Synopsis

```text
topo-tools edge-extend [OPTIONS] INPUT_FILE [OUTPUT_FILE]
```

## Description

Each polygon grows into the empty space next to it (coastlines, water bodies, disputed areas) using Voronoi diagrams, so the layer covers a continuous area. OUTPUT_FILE defaults to INPUT_FILE with an "_extended" suffix.

## Options

- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|lines|attempt|merge|outputs]`: Run only this step of the tool, for debugging.

## Examples

Basic run, output name chosen automatically:

```sh
  topo-tools edge-extend example.geojson
```

Explicit output:

```sh
topo-tools edge-extend example.gpkg example_extended.gpkg
```

Stop with an error if the output already exists:

```sh
topo-tools edge-extend example.parquet example_extended.parquet --overwrite=false
```
