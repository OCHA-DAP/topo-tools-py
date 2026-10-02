---
title: "code-update"
description: "Code a new release so units that carry over keep their previous codes."
sidebar:
  order: 5
---

Code a new release so units that carry over keep their previous codes.

## Synopsis

```text
topo-tools code-update [OPTIONS] OLD_FILE NEW_FILE [OUTPUT_FILE] [CHANGELOG_FILE]
```

## Description

OLD_FILE is the previous release, already coded. NEW_FILE is the new release. Unchanged units keep their codes, changed units get new ones, and no code is ever given to a different unit. OUTPUT_FILE, the new release with codes, defaults to NEW_FILE with a "_coded" suffix. CHANGELOG_FILE, a table of what happened to each code, defaults to OUTPUT_FILE with a "_changelog" suffix and is always written.

## Options

- `--root-code TEXT`: Code at the start of every code. Detected from OLD_FILE's codes if omitted.
- `--delimiter TEXT`: One character between the parts of a code, or '' for none. Detected from OLD_FILE's codes if omitted.
- `--min-width TEXT`: How many digits each level's number is padded to with zeros: 3, 2,2,4 or auto. Detected from OLD_FILE's codes if omitted.
- `--name-field-a TEXT`: Name column of each level in OLD_FILE, with {n} for the level number, e.g. 'adm{n}_name'. Give it with `--code-field-a`. Without both, levels are detected from the data.
- `--code-field-a TEXT`: Code column of each level in OLD_FILE, with {n} for the level number, e.g. 'adm{n}_pcode'. Give it with `--name-field-a`. Without both, levels are detected from the data.
- `--name-field-b TEXT`: Name column of each level in NEW_FILE, with {n} for the level number. Give it with `--code-field-b`. Without both, levels are detected from the data.
- `--code-field-b TEXT`: Code column of each level in NEW_FILE, with {n} for the level number. A level with names but no code column gets codes made from its names. Give it with `--name-field-b`. Without both, levels are detected from the data.
- `--code-column-a TEXT`: Code column in OLD_FILE used by `--link-by-code`. Defaults to each level's code column.
- `--code-column-b TEXT`: Code column in NEW_FILE used by `--link-by-code`. Defaults to each level's code column.
- `--name-column-a TEXT`: Name column in OLD_FILE used by `--link-by-name`. Defaults to each level's name column.
- `--name-column-b TEXT`: Name column in NEW_FILE used by `--link-by-name`. Defaults to each level's name column.
- `--tau-match FLOAT`: Smallest share of a unit's area that must overlap another unit for the two to count as related. [default: 0.8]
- `--tau-same FLOAT`: Smallest overlap, as shared area divided by combined area, for a matched pair to count as the same shape rather than modified. [default: 0.98]
- `--link-by-code`: Also match units that have the same code in both versions, when that code is unique.
- `--link-by-name`: Also match units that have the same name in both versions, when that name is unique.
- `--link-mode [either|both]`: With both `--link-by-code` and `--link-by-name`, match on either one or only on both. [default: either]
- `--overwrite BOOLEAN`: Replace output files that already exist. Pass `--overwrite=false` to stop with an error instead. [default: True]
- `--threads INTEGER`: Number of threads DuckDB uses (default: all CPU cores).
- `--debug`: Keep intermediate tables, export them to Parquet, and log the time and memory each query takes.
- `--tmp-dir TEXT`: Folder for the working DuckDB database and intermediate files (default: a new temporary folder, deleted afterwards unless `--debug` is set).
- `--step [inputs|levels|process|outputs]`: Run only this step of the tool, for debugging.

## Examples

Basic run, code format and levels detected from OLD_FILE:

```sh
  topo-tools code-update admin1_old.geojson admin1_new.geojson
```

Also match units by a shared source ID, for units that moved:

```sh
topo-tools code-update old.gpkg new.gpkg --link-by-code \
  --code-column-a srcid --code-column-b srcid
```
