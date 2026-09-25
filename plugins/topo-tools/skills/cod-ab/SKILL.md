---
name: cod-ab
description: Clean, code, and package COD-AB administrative boundary polygons with topo-tools (schema mapping, topology repair, hierarchical coding, edge-fitting, hierarchy fill, cartographic packaging).
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
3. Create `01_inputs/`, `02_working/`, and `03_outputs/` at the workspace
   root if missing, then check `01_inputs/` and `02_working/`.
   - Files exist in `01_inputs/`: for each, ask the user its country and
     whether it's the new source or the old (previous) version, plus a
     third option, a file returned by an external reviewer, only when
     `03_outputs/` already holds a candidate for that country (then ask
     which candidate it responds to, see [Candidates](#candidates)). For a
     new source, run
     `uv run <skill-dir>/scripts/fetch_reference.py {iso3}`: it writes the
     HDX release to `02_working/{iso3}/{version}/00a_old/` and prints
     `ref_version`/`version` (`ref_version=none version=v01` when HDX has
     none). If the user also dropped an old version, ask which one to
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
     converts cleanly. On a failure, stop and keep the file.
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
   through `05_packaging/`). Each stage's own tool output,
   and, where produced, its issues file, is the audit trail, no separate
   report file. A stage counts as complete only when its defining output
   exists, not just an issues file (a stage that ran
   `topo-clean`/`edge-match`/`code-refactor` and stopped at the issues
   file, without writing the tool's own `OUTPUT_FILE`, is in progress,
   not done: resume there, don't skip past it):

   | Stage | Defining output |
   | --- | --- |
   | `01_schema/` | `{iso3}_admin{n}.parquet` for every supplied level, plus `{iso3}_admin{n}_issues.parquet` only where `schema-join` wrote issues; no other parquet |
   | `02_geometry/` | the topo-cleaned file (edge-match is conditional, skip if not applicable) |
   | `03_codes/` | the code-refactored file |
   | `04_names/` | the names issues file (present, any row count, even zero, since this stage has no other output) |
   | `05_packaging/` | one parquet per output layer |

   The highest-numbered stage with its defining output present marks the
   last completed stage; resume at the next one. No stage folders yet
   (only `00a_old/`/`00b_new/`): start at stage 1.
5. If starting at stage 1 (no stage folders exist yet, per step 4), inspect
   the source file(s) in `00b_new/` before proposing stage 1. For a
   multi-layer archive (GDB, GPKG), list layers first. For each candidate
   file/layer, report feature count, column names, and a few sample
   p-code/name values via DuckDB. Use the deepest file/layer as the base,
   the only one carried past stage 1 (every ancestor level is derived from it by
   dissolve in stage 2), and the country's ISO2 code as stage 3's
   `--root-code` under the legacy p-code scheme. State both before
   continuing, with the base's name, feature count, and why it qualifies.
   Ask the user to pick a shallower base only if the deepest one looks
   partial or low quality (doesn't cover the whole country, has missing
   codes/names, or far fewer units than its parent level implies; judge
   from feature counts and total bounds, never file sizes). Stage 1
   normalizes every supplied level into
   `01_schema/{iso3}_admin{n}.parquet` (one file per level, updated in
   place by each step, never a suffixed copy). Only the base continues past
   stage 1. The others are `schema-join`'s parent layers. Skip
   this step when resuming past stage 1.

## Stages

Work through these in order, writing each stage's own output into its
matching `02_working/{iso3}/{version}/0N_stage/` folder (the linked guides below
use generic placeholder filenames, substitute your own paths there).

1. [Map the source schema](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/01-schema.md)
2. [Clean geometry](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/02-geometry.md)

   Always ask whether any large `topo-detect` gap is a lake or other
   water body left outside every unit, showing the largest gaps (area,
   width, PNG render) and whether `00a_old/` has the same holes. "No"
   means `--maximum-gap-width all`; "yes" means no flag.
3. [Assign hierarchical codes](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/03-codes.md)
4. [Review names](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/04-names.md)
5. [Package for output](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/05-packaging.md)

## Candidates

After stage 5, export each release candidate (`rc`) sent for review:

1. Set `{NN}` to the next candidate number after the highest in
   `03_outputs/{iso3}/{version}/`, starting at `01`. Never overwrite an
   existing candidate.
2. Write every `05_packaging/` parquet as one layer of
   `03_outputs/{iso3}/{version}/{iso3}_{version}_rc{NN}.gdb` with
   `uv run <skill-dir>/scripts/convert.py to-gdb {gdb} {parquet}...`.
3. Write `{iso3}_{version}_rc{NN}_review.gdb` alongside it with
   `convert.py to-gdb {gdb} {stage}={issues.parquet}... change={change.parquet}`:
   each stage's issues file as a layer named after its stage without the
   number prefix (`schema`, `geometry`, ...), plus `change` output
   comparing this candidate against the previous one (`rc01`: against
   `00a_old/`, skipped when absent).

For a file returned by the reviewer (step 3 of Setup), ask which stage it
re-enters at, place it there as GeoParquet or CSV, and rerun from that
stage.
