---
name: cod-ab
description: Clean, code, and package COD-AB administrative boundary polygons with topo-tools (schema mapping, topology repair, hierarchical coding, edge-fitting, hierarchy fill, cartographic packaging).
---

Guide the user through cleaning and reconciling a COD-AB administrative
boundary layer with topo-tools.

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
   `uv init` there, `uv add topo-tools pyogrio`, add a
   `[tool.topo-tools-cod-ab]` table to the new `pyproject.toml`, then the
   same refresh. Run every command below via `uv run topo-tools ...`.
   `pyogrio` covers layer introspection on multi-layer source files (GDB,
   GPKG) throughout this skill.
3. Create the root-level `drop/` folder if it doesn't already exist, then
   check it and `data/` for existing country folders.
   - Files exist in `drop/`: for each, ask the user which country it
     belongs to, run `uv run <skill-dir>/scripts/fetch_reference.py {iso3}`
     to determine `{ref_version}`/`{version}` and fetch the HDX reference
     layers, then move the file to `data/{iso3}/{version}/00-originals/`.
   - `drop/` is empty and no country folders exist in `data/`: ask the
     user which country they want to start processing, or point them to
     `drop/` to add source files.
   - `drop/` is empty and exactly one country folder exists: ask the
     user to confirm they want to continue working on it.
   - `drop/` is empty and multiple country folders exist: ask the user
     which one to work on.

   Set `{iso3}` to the lowercase ISO3 country code for the rest of this
   skill. `{ref_version}` is the most recent HDX-published release for
   that country; `{version}` is the next release being prepared (e.g.
   `v03` after `v02`), both determined automatically from HDX, never
   asked of the user.
4. Check `data/{iso3}/{version}/` for existing stage folders
   (`01-schema/` through `05-packaging/`). Each stage's own tool output,
   and, where produced, its issues file, is the audit trail, no separate
   report file. A stage counts as complete only when its defining output
   exists, not just an issues file (a stage that ran
   `topo-clean`/`edge-match`/`code-refactor` and stopped at the issues
   file, without writing the tool's own `OUTPUT_FILE`, is in progress,
   not done: resume there, don't skip past it):

   | Stage | Defining output |
   | --- | --- |
   | `01-schema/` | the schema-refactored file |
   | `02-geometry/` | the topo-cleaned file (edge-match and the dissolve check are conditional, skip if not applicable) |
   | `03-codes/` | the code-refactored file |
   | `04-names/` | the names issues file (present, any row count, even zero, since this stage has no other output) |
   | `05-packaging/` | the `release/` bundle |

   The highest-numbered stage with its defining output present marks the
   last completed stage; resume at the next one. No stage folders yet
   (only `00-originals/`): start at stage 1.
5. If starting at stage 1 (no stage folders exist yet, per step 4), inspect
   the raw file(s) in `00-originals/` before proposing stage 1. For a
   multi-layer archive (GDB, GPKG), list layers first. For each candidate
   file/layer, report feature count, column names, and a few sample
   p-code/name values via DuckDB. Confirm with the user: which level is
   the base (the authoritative geometry level, ancestors are derived by
   dissolve in stage 2) and the country's ISO2 code (used as stage 3's
   `--root-code` under the legacy p-code scheme). Skip this step when
   resuming past stage 1.

## Stages

Work through these in order, writing each stage's own output into its
matching `data/{iso3}/{version}/0N-stage/` folder (the linked guides below
use generic placeholder filenames, substitute your own paths there).

1. [Map the source schema](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/01-schema.md)
2. [Clean geometry](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/02-geometry.md)
3. [Assign hierarchical codes](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/03-codes.md)
4. [Review names](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/04-names.md)
5. [Package for output](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/05-packaging.md)
