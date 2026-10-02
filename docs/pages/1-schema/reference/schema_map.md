---
title: "schema-map"
description: "Rename a layer's admin columns to a standard schema, using a crosswalk."
sidebar:
  order: 3
---

Rename a layer's admin columns to a standard schema, using a crosswalk.

## Synopsis

```text
topo-tools schema-map [OPTIONS] INPUT_FILE [OUTPUT_FILE]
```

## Description

The admin levels and which columns hold codes or names are worked out from the data, not the column names. The result is written as a crosswalk CSV and applied. To adjust it, edit the CSV (change a target, blank it to drop the column, move rows to reorder) and run again with `--csv`. OUTPUT_FILE defaults to INPUT_FILE with a "_mapped" suffix.

## Options

- `--csv TEXT`: Apply this crosswalk CSV, usually an edited one, instead of making one. Output columns follow its row order.
- `--csv-output TEXT`: Path for the crosswalk CSV. Defaults to INPUT_FILE with a "_crosswalk.csv" ending.
- `--map-only`: Write only the crosswalk CSV, not the renamed layer.
- `--name-field TEXT`: Target name for each level's name column, with {n} for the level number. Give it with `--code-field`. Default: 'adm{n}_name'.
- `--code-field TEXT`: Target name for each level's code column, with {n} for the level number. Give it with `--name-field`. Default: 'adm{n}_code'.
- `--level INTEGER RANGE`: Admin level of the file's finest units, used to number the levels. By default the coarsest level is 1, or 0 for a column with a single country value. [x>=0]
- `--layer TEXT`: Layer to read from a file with several layers, such as a FileGDB. Needed only when the file has more than one layer with geometry.
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|map|apply|outputs]`: Run only this step of the tool, for debugging.

## Examples

Map and apply, output names chosen automatically:

```sh
  topo-tools schema-map example.geojson
```

Apply an edited crosswalk:

```sh
topo-tools schema-map example.geojson --csv example_crosswalk.csv
```

Only write the crosswalk, for a file whose finest level is admin3:

```sh
topo-tools schema-map admin3.geojson --map-only --level 3
```

Use different target column names:

```sh
topo-tools schema-map example.geojson --name-field adm{n}_name \
  --code-field adm{n}_pcode
```
