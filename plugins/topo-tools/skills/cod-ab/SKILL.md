---
name: cod-ab
description: Clean, code, and package COD-AB administrative boundary polygons with topo-tools (schema mapping, topology repair, edge matching, hierarchical coding, name review, cartographic packaging).
---

Guide the user through cleaning and reconciling a COD-AB administrative
boundary layer with topo-tools. Ask only where no documented default
exists or a step can't be undone; otherwise state the choice and
continue. Ask with the AskUserQuestion tool, in terms of the data, never
flag names, offering your inferred answer as the first, recommended
option.

File a GitHub issue against this repo, rather than patching around it,
whenever a command crashes or raises unexpectedly, output looks wrong (bad
geometry, a miscount, a column that shouldn't be null), or behavior differs
across platforms (macOS/Linux/Windows path handling, available memory): use
the
[bug report template](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/.github/ISSUE_TEMPLATE/bug_report.yml).
When a stage needs something `topo-tools` can't currently do, use the
[feature request template](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/.github/ISSUE_TEMPLATE/feature_request.yml)
instead. See
[CONTRIBUTING.md](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/CONTRIBUTING.md)
for either.

Whenever a step writes Parquet with DuckDB directly, not through a
topo-tools command, match topo-tools' own output: name the geometry column
`geometry` and write with `COPY ... TO '<out>.parquet' (FORMAT PARQUET,
COMPRESSION ZSTD, COMPRESSION_LEVEL 15, GEOPARQUET_VERSION 'V2')`. Convert
source files to GeoParquet and GeoParquet to GDB only with
`uv run <skill-dir>/scripts/convert.py`. Never read a GDB with DuckDB's
`ST_Read`, which returns 0 rows on Esri-authored GDBs.

`<skill-dir>` is this skill's own directory. If `<skill-dir>/scripts/`
doesn't exist (this file was pasted or fetched, not installed as a
plugin), use
`https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/plugins/topo-tools/skills/cod-ab`
as `<skill-dir>` in every command below, e.g.
`uv run https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/plugins/topo-tools/skills/cod-ab/scripts/convert.py`.

## Setup

1. Check whether `uv` resolves on `PATH`. If not, install it with its
   platform installer (`curl -LsSf https://astral.sh/uv/install.sh | sh`
   on macOS/Linux, `powershell -ExecutionPolicy ByPass -c "irm
https://astral.sh/uv/install.ps1 | iex"` on Windows).
2. Check whether the current directory's `pyproject.toml` has a
   `[tool.topo-tools-cod-ab]` table. If it does, treat the environment as
   already prepared: run `uv lock --upgrade && uv sync` to refresh
   versions, then continue. If it doesn't (no `pyproject.toml`, or one
   without that table), help set up a dedicated working directory:
   `uv init --bare --vcs none` there, `uv add topo-tools`, add a
   `[tool.topo-tools-cod-ab]` table to the new `pyproject.toml`, then the
   same refresh. Run every command below via `uv run topo-tools ...`.
3. Create `00_shared/`, `01_inputs/`, `02_working/`, and `03_outputs/`
   at the workspace root if missing, then check `01_inputs/` and `02_working/`.
   - Files exist in `01_inputs/`: for each, ask the user its country and
     whether it's the new source or the old (previous) version, plus a
     third option, a file returned by an external reviewer, only when
     `03_outputs/` already holds a candidate for that country (then ask
     which candidate it responds to, see [Candidates](#candidates)). For a
     new source, run
     `uv run <skill-dir>/scripts/fetch_reference.py {iso3}`: it writes the
     previous release from `source.coop/hdx/cod-ab/matched` to
     `02_working/{iso3}/{version}/00a_old/` (one `{iso3}_admin{n}.parquet`
     per level, plus `{iso3}_admin0.parquet` dissolved from its admin1) and
     prints `ref_version`/`version` (`ref_version=none version=v01` when
     there's none). If the user also dropped an old version, ask which one to
     compare against. For a user-supplied old version, ask its version;
     `{version}` is the next one after it. Propose `{version}` and have the
     user confirm it, renaming the folder if they change it. Extract a
     `.zip` into `01_inputs/` first with
     `uv run python -m zipfile -e {zip} 01_inputs/`, not `unzip` (it
     misreads non-UTF-8 member names), and treat each dataset inside it
     (`.shp`, `.gdb`, `.gpkg`, `.geojson`) as its own file. Convert each
     file with
     `uv run <skill-dir>/scripts/convert.py to-parquet {file} 02_working/{iso3}/{version}/{00a_old|00b_new}/`.
     It writes one GeoParquet per layer, named after its source with
     accents stripped, and exits non-zero when a layer's written feature
     count doesn't match its source. If the source has no `.cpg` file and
     accented or typographic characters come out wrong (e.g. `’` or `€`
     missing), delete its GeoParquet and rerun with `--encoding cp1252`
     (or the source's actual codepage). Delete the file from `01_inputs/` (a
     zip together with everything extracted from it) only after it
     converts cleanly. On a failure, stop and keep the file. When
     `00a_old/` ends up without `{iso3}_admin0.parquet` and `00_shared/`
     holds no admin0 GeoParquet, ask the user to put their own admin0 file
     in `00_shared/`, never proposing one. Convert any other format with
     `uv run <skill-dir>/scripts/convert.py to-parquet {file} 00_shared/`,
     and delete the original once it converts cleanly.
   - `01_inputs/` is empty and `02_working/` has no country folders: ask
     the user which country to start, or point them to `01_inputs/`.
   - `01_inputs/` is empty and exactly one country folder exists: ask the
     user to confirm they want to continue it.
   - `01_inputs/` is empty and multiple country folders exist: ask which
     one to work on.

   Set `{iso3}` to the lowercase ISO3 code and `{version}` to the
   confirmed `vNN` for the rest of this skill. `00a_old/` is absent when
   there's no previous version.
4. Check `02_working/{iso3}/{version}/` for stage folders (`01_schema/`
   through `06_packaging/`). Each stage's own tool output,
   and, where produced, its issues file, is the audit trail, no separate
   report file. A stage counts as complete only when its defining output
   exists, not just an issues file (a stage that ran
   `topo-clean`/`edge-match`/`code-create` and stopped at the issues
   file, without writing the tool's own `OUTPUT_FILE`, is in progress,
   not done: resume there, don't skip past it):

   | Stage | Defining output |
   | --- | --- |
   | `01_schema/` | `{iso3}_admin{n}.parquet` for every supplied level below admin0, plus `{iso3}_admin{n}_issues.parquet` only where `schema-join` wrote issues; no other parquet |
   | `02_topology/` | the topo-cleaned file (the finer-level edge-match is conditional, skip if not applicable) |
   | `03_edge_matching/` | the edge-matched file |
   | `04_codes/` | the coded file |
   | `05_names/` | the name-cleaned file plus `{iso3}_admin{n}_name_issues.parquet` from the final `name-detect` check (any row count, even zero) |
   | `06_packaging/` | one parquet per output layer |

   The highest-numbered stage with its defining output present marks the
   last completed stage; resume at the next one. No stage folders yet
   (only `00a_old/`/`00b_new/`): start at stage 1.
5. If starting at stage 1 (no stage folders exist yet, per step 4), inspect
   the source file(s) in `00b_new/` before proposing stage 1. For a
   multi-layer archive (GDB, GPKG), list layers first. For each candidate
   file/layer, report feature count, column names, and a few sample
   p-code/name values via DuckDB. Use the deepest file/layer as the base,
   the only one carried past stage 1 (every ancestor level is derived from it by
   dissolve in stage 6), and the country's ISO2 code as stage 4's
   `--root-code`. State both before continuing, with the base's name, feature count, and why it qualifies.
   Ask the user to pick a shallower base only if the deepest one looks
   partial or low quality (doesn't cover the whole country, has missing
   codes/names, or far fewer units than its parent level implies; judge
   from feature counts and total bounds, never file sizes). Stage 1
   normalizes every supplied level below admin0 into
   `01_schema/{iso3}_admin{n}.parquet` (one file per level, updated in
   place by each step, never a suffixed copy). Only the base continues past
   stage 1. The others are `schema-join`'s join layers. Leave the admin0
   file (one feature) out of stage 1. Skip
   this step when resuming past stage 1.

## Stages

Work through these in order, writing each stage's own output into its
matching `02_working/{iso3}/{version}/0N_stage/` folder (the linked guides below
use generic placeholder filenames, substitute your own paths there).

Save every rendered image in its stage's `previews/` folder (e.g.
`02_topology/previews/`) and give the user its path. To show specific
units, run `uv run <skill-dir>/scripts/preview.py features {layer} {png} --where {sql} --label {name column}`,
using the first name column. For any other render, run
`preview.py basemap {xmin} {ymin} {xmax} {ymax} {stem}` and draw over its
PNGs using the JSON sidecar's pixel mapping and font, never by importing
`preview.py`.

1. [Schema](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/1-schema/how-to.md)
2. [Topology](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/2-topology/how-to.md)

   Always ask whether any large `topo-detect` gap is a lake or other
   water body left outside every unit. Render the largest gaps with
   `uv run <skill-dir>/scripts/preview.py issues {issues} 02_topology/previews/ --units {input}`,
   read each PNG to judge water against land, and show the user each
   gap's area, width and PNG path, plus whether `00a_old/` has the same
   holes. "No" means `--maximum-gap-width all`; "yes" means no flag.
3. [Edge matching](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/3-edge/how-to.md)

   Take the reference admin0 from the admin0 file in `00_shared/` (ask
   which when there are several), which may cover many countries, else
   `00a_old/{iso3}_admin0.parquet`. When neither exists, ask for one as in
   setup step 3. Extract the country from `00_shared/` with DuckDB
   (`spatial` loaded), filtering on a column whose values include
   `{iso3}` in any case. When none does, ask whether the whole file is
   this country (then drop the `WHERE`), or which column and value select
   it; when matching columns select different features, ask which:
   `COPY (SELECT * FROM '00_shared/{admin0}.parquet' WHERE trim(upper("{column}"::VARCHAR)) = upper('{iso3}')) TO '02_working/{iso3}/{version}/03_edge_matching/{iso3}_admin0.parquet' (FORMAT PARQUET, COMPRESSION ZSTD, COMPRESSION_LEVEL 15, GEOPARQUET_VERSION 'V2')`.

   After `edge-match`, measure each stage 2 unit's area inside the
   reference admin0 with DuckDB (`spatial` loaded,
   `SET geometry_always_xy = true`, `ST_Area_Spheroid`). A unit with none
   inside is dropped (their count matches the issues file's `clip-empty`
   rows); one with under half inside is partly cut. Dropping units is a
   defect: when any unit is dropped, stop and report

   - the dropped units' count and names
   - every parent unit, at each coarser level, whose units were all
     dropped (grouped by its code column, or its name column when it has
     no codes)
   - the partly cut units' count, as information
   - the total area before and after
   - each cluster of dropped units (number, unit count, centre, parent
     names) with its PNG path, rendered by
     `preview.py features {stage 2 file} 03_edge_matching/previews/{iso3}_dropped.png --cluster --label {first name column} --units {stage 2 file} --reference {admin0} --where "ST_Area(ST_Intersection(geometry, (SELECT ST_Union_Agg(geometry) FROM read_parquet('{admin0}')))) = 0"`

   Then ask the user to choose: continue without these units; code the
   full geometry first (stages 4 and 5 run on the stage 2 file); or rerun
   stage 3 with a different admin0 the user puts in `00_shared/` (never
   propose one). Continue only on an explicit choice, and ask again when
   resuming at stage 4 before `04_codes/` has output. Render the
   output's largest `gap` and `detached-part` rows with
   `preview.py issues {issues} 03_edge_matching/previews/ --units {output} --reference {admin0} --kind {kind}`
   and check them against both base layers before accepting the output.
4. [Codes](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/4-codes/how-to.md)

   Show a few code values from each level of the file to code, and ask
   whether they are source codes to keep as given (issued by the government
   or agreed with the country office). Then:

   - Yes: `code-create --root-code {ISO2} --delimiter '' --min-width auto --source-codes embed`
     with `--code-field`/`--name-field` templates naming each level's
     columns. Ignore `00a_old/`.
   - No, with `00a_old/`: `code-update`, with the base-level file in
     `00a_old/` as OLD.
   - No, without `00a_old/`: `code-create --root-code {ISO2} --delimiter '' --min-width auto`,
     adding `--source-codes copy` when the codes are another
     organisation's IDs.

   Code the stage 2 file in place of the stage 3 output when the user
   chose to code the full geometry first.
5. [Names](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/5-names/how-to.md)

   Run `name-clean`, then read every name in the cleaned file, not only the
   flagged ones, in batches by parent unit. Judge each `warn` row and look
   for what the checks can't catch (typos, inconsistent spellings across
   levels or language columns, casing). Propose a fix per unit with its
   code, apply the ones the user approves, then re-check with `name-detect`.
   Write both reports as `.parquet`: `{iso3}_admin{n}_name_fixes.parquet`
   from `name-clean` and `{iso3}_admin{n}_name_issues.parquet` from the
   final `name-detect`.
6. [Packaging](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/6-packaging/how-to.md)

   When the name-cleaned file in `05_names/` has more units than the stage 3
   output (the full geometry was coded first), ask whether to package it
   as is, or rerun `edge-match` on it with the same admin0, overwriting
   the stage 3 output, and package that.

## Candidates

After stage 6, export each release candidate (`rc`) sent for review:

1. Set `{NN}` to the next candidate number after the highest in
   `03_outputs/{iso3}/{version}/`, starting at `01`. Never overwrite an
   existing candidate.
2. Write every `06_packaging/` parquet as one layer of
   `03_outputs/{iso3}/{version}/{iso3}_{version}_rc{NN}.gdb` with
   `uv run <skill-dir>/scripts/convert.py to-gdb {gdb} {parquet}...`.
3. Write `{iso3}_{version}_rc{NN}_review.gdb` alongside it with
   `convert.py to-gdb {gdb} {stage}={issues.parquet}... change={change.parquet}`:
   each stage's issues file as a layer named after its stage without the
   number prefix (`schema`, `topology`, ...), plus `change` output
   comparing this candidate against the previous one (`rc01`: against
   `00a_old/`, skipped when absent).

For a file returned by the reviewer (step 3 of Setup), ask which stage it
re-enters at, place it there as GeoParquet or CSV, and rerun from that
stage.
