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
   `uv init` there, `uv add topo-tools`, add a `[tool.topo-tools-cod-ab]`
   table to the new `pyproject.toml`, then the same refresh. Run every
   command below via `uv run topo-tools ...`.

## Stages

Work through these in order:

1. [Map the source schema](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/01-map-schema.md)
2. [Fix internal topology](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/02-fix-topology.md)
3. [Assign hierarchical codes](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/03-assign-codes.md)
4. [Fit a finer level into one district](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/04-fit-finer-level.md)
5. [Fill attributes and derive ancestor levels](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/05-fill-and-derive-ancestors.md)
6. [Package for output](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/docs/pages/how-to/06-package-for-output.md)
