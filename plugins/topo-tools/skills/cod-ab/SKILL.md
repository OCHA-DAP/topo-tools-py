---
name: cod-ab
description: Clean, code, and package COD-AB administrative boundary polygons with topo-tools (schema mapping, topology repair, hierarchical coding, edge-fitting, hierarchy fill, cartographic packaging).
---

Guide the user through cleaning and reconciling a COD-AB administrative
boundary layer with topo-tools.

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

## Stages

Work through these in order:

1. [Map the source schema](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/01-map-schema.md)
2. [Fix internal topology](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/02-fix-topology.md)
3. [Assign hierarchical codes](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/03-assign-codes.md)
4. [Fit a finer level into one district](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/04-fit-finer-level.md)
5. [Fill attributes and derive ancestor levels](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/05-fill-and-derive-ancestors.md)
6. [Package for output](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/06-package-for-output.md)
