---
title: "edge-clip"
description: "Clip an input layer to the overlay polygon it overlaps most."
sidebar:
  order: 4
---

Clip an input layer to the overlay polygon it overlaps most.

## Synopsis

```text
topo-tools edge-clip [OPTIONS] INPUT_FILE OVERLAY_FILE [OUTPUT_FILE]
```

## Description

The whole input file is matched to the one overlay polygon most of it falls in, then clipped to that polygon's shape. OUTPUT_FILE defaults to INPUT_FILE with a "_clipped" suffix.

## Options

- `--issues-file TEXT`: Path for the issues report, written only with `--match-column` or `--overlay-match-column`. Defaults to OUTPUT_FILE with an "_issues" suffix.
- `--name TEXT`: Name used for the run's working tables and temporary files.
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|assign|clip|outputs]`: Run only this step of the tool, for debugging.
- `--match-column TEXT`: Column in both layers, such as a p-code, used to match input polygons to overlay polygons. It wins over overlap where the two disagree. Can't be combined with `--overlay-match-column` or `--input-match-column`.
- `--overlay-match-column TEXT`: Matching column in the overlay, when its name differs from the input's. Give it with `--input-match-column`.
- `--input-match-column TEXT`: Matching column in the input, when its name differs from the overlay's. Give it with `--overlay-match-column`.
- `--carry-column TEXT`: Overlay column to copy onto each matched input polygon. Repeat it or separate columns with commas.
- `--original TEXT`: The original layer before extension. It decides whether a piece cut off by clipping is merged into a neighbor. Without it, such pieces are only reported.

## Examples

Clip an input layer against an overlay layer:

```sh
topo-tools edge-clip input.parquet adm1.geojson
```

Explicit output:

```sh
topo-tools edge-clip input.parquet adm1.geojson clipped.parquet
```

Match on a shared p-code column, overriding overlap where they disagree:

```sh
topo-tools edge-clip input.parquet adm1.geojson --match-column pcode
```

Copy overlay columns onto every matched input polygon:

```sh
topo-tools edge-clip input.parquet adm1.geojson --carry-column iso_3,adm0_name
```
