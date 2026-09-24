# topo-tools

[![CI](https://github.com/OCHA-DAP/topo-tools-py/actions/workflows/ci.yml/badge.svg)](https://github.com/OCHA-DAP/topo-tools-py/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/topo-tools)](https://pypi.org/project/topo-tools/)
[![Python versions](https://img.shields.io/pypi/pyversions/topo-tools)](https://pypi.org/project/topo-tools/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

![World ADM0 boundaries extended with Voronoi-filled coastline](https://raw.githubusercontent.com/OCHA-DAP/topo-tools-py/main/img/wld_01.png)

`topo-tools` is a collection of DuckDB-powered geospatial topology utilities
for cleaning and reconciling administrative boundary polygons, usable from
the CLI or as a Python package.

Full documentation: <https://ocha-dap.github.io/topo-tools-py/>

| Tool | Description |
| --- | --- |
| **schema-crosswalk** | map and apply a source to target schema crosswalk |
| **schema-map** | infer a source to target schema crosswalk |
| **schema-refactor** | apply a schema crosswalk |
| **schema-fill** | fill down admin-hierarchy columns |
| **schema-join** | copy parent admin-hierarchy columns onto each child |
| **topo-clean** | detect and fix gap/overlap defects |
| **topo-detect** | detect gap/overlap defects |
| **edge-match** | fit a child layer into a parent layer |
| **edge-extend** | fill gaps with a Voronoi extension |
| **edge-mosaic** | re-clip an extended child layer into a new parent |
| **edge-clip** | clip a child layer to its parent |
| **edge-stitch** | close seams in a tiled layer |
| **change** | classify changes between two polygon layer versions |
| **package** | dissolve, label, and line-ify a layer in one call |
| **package-polygons** | dissolve a layer into coarser admin levels |
| **package-points** | one label point per admin unit |
| **package-lines** | deduplicated admin boundary lines |

## Installation

Install with `uv` (recommended):

```sh
uv tool install topo-tools   # CLI
uv add topo-tools            # Python library
```

Or with `pip`/`pipx`:

```sh
pip install topo-tools       # CLI or library
pipx install topo-tools      # CLI
```

On macOS/Linux, `topo-tools` is also available via Homebrew, no Python
tooling required:

```sh
brew install OCHA-DAP/topo-tools/topo-tools
```

## Supported Formats

Polygon inputs/outputs: GeoParquet (`.parquet`), GeoPackage (`.gpkg`),
Shapefile (`.shp`), GeoJSON (`.geojson`). Output format matches input format.
`change`'s tabular changelog is CSV or GeoParquet only; its spatial overlay
layer supports the same four formats as the other tools.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup.
