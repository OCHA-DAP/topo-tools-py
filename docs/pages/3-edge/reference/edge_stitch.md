---
title: "edge-stitch"
description: "Close the seams between pieces of a layer that was clipped in parts."
sidebar:
  order: 5
---

Close the seams between pieces of a layer that was clipped in parts.

## Synopsis

```text
topo-tools edge-stitch [OPTIONS] INPUT_FILE [OUTPUT_FILE]
```

## Description

Removes the slivers and overlaps left where clipped pieces meet. OUTPUT_FILE defaults to INPUT_FILE with a "_stitched" suffix. It's required when INPUT_FILE is a pattern matching more than one file, or when `--input` is given.

## Options

- `--input TEXT`: Another clipped file to stitch together with INPUT_FILE. Repeat it or separate files with commas.
- `--issues-file TEXT`: Path for the issues report. Defaults to OUTPUT_FILE with an "_issues" suffix.
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|clean|outputs]`: Run only this step of the tool, for debugging.
- `--fill-schema`: Before writing the output, fill each row's empty finer admin columns from its coarser ones and add a column with the row's own admin level. Set the columns with `--name-field` and `--code-field`, and the level column's name with `--depth-column`.
- `--name-field TEXT`: Name column of each level, with {n} for the level number, e.g. 'adm{n}_name'. Needs `--fill-schema` and `--code-field`. Without both, levels are detected from the data.
- `--code-field TEXT`: Code column of each level, with {n} for the level number, e.g. 'adm{n}_code'. Needs `--fill-schema` and `--name-field`. Without both, levels are detected from the data.
- `--depth-column TEXT`: Name of the added column holding each row's own admin level. Needs `--fill-schema`. [default: adm_lvl]

## Examples

Basic run, output name chosen automatically:

```sh
topo-tools edge-stitch tiled.geojson
```

Explicit output:

```sh
topo-tools edge-stitch tiled.gpkg stitched.gpkg
```

Stitch every clipped file into one output:

```sh
topo-tools edge-stitch "tmp/clipped/*.parquet" stitched.parquet
```

List files instead of a pattern (repeat `--input` or use commas):

```sh
topo-tools edge-stitch afg.parquet stitched.parquet \
  --input ago.parquet,are.parquet
```

Stop with an error if the output already exists:

```sh
topo-tools edge-stitch tiled.parquet stitched.parquet --overwrite=false
```
