# CLAUDE.md

## Project Overview

`topo-tools` is a Python package of DuckDB-powered geospatial topology utilities,
`pip install`-able and importable, mirroring the organization of the sister JS app
at `../topo-tools` (a DuckDB-WASM web app with the same tools). It ships eighteen
tools, all used for improving administrative boundary datasets and matching
sub-national boundaries to national boundaries (import-linter contracts
governing which tool may depend on which are in `docs/pages/reference/shared.md`).
Tools are named `{group}-{verb}`: **edge** (boundary-fitting between layers),
**topo** (single-layer topology defects), **schema** (column crosswalking),
and **package** (cartographic derivatives for web maps); `change` and bare
`package` stand alone for now, as do `code-refactor` and `code-update`. Four
are primitives, each standalone AND reused internally by the composite tools
below them:

- **edge-extend**: extends polygon boundaries outward using Voronoi diagrams, producing a complete coverage layer that fills gaps (coastlines, disputed areas, water bodies).
- **edge-clip**: assigns each child to its parent (always `assign-one`), then clips it to that parent's geometry, one `parent_fid` at a time in its own subprocess; a strict one-children-file/one-parent-file/one-output primitive (`edge-mosaic` owns batching many children files against one shared parent load, see `docs/adr/0080`). See `docs/pages/explanation/edge_clip.md`.
- **edge-stitch**: closes seams in an already-tiled layer with one whole-table `ST_CoverageClean` pass. See `docs/pages/explanation/edge_stitch.md`.
- **topo-detect**: scans a single polygon layer for gap/overlap coverage defects and reports them, without fixing anything. See `docs/pages/explanation/topo_detect.md`.
- **package-polygons**: dissolves a polygon layer into every detected coarser admin level in a single call, levels auto-detected structurally by default (or via an explicit `--name-field`/`--code-field` pair), reusing the `core.dissolve` leaf's stage functions directly, once per level. See `docs/pages/explanation/package_polygons.md`.
- **package-points**: one label point per admin unit per detected level, using the pole of inaccessibility (always interior, unlike a centroid), combined into a single output file. See `docs/pages/explanation/package_points.md`.
- **package-lines**: one deduplicated line network of admin boundaries (shared between two units, or exterior to all of them), tagged by adjacency and the coarsest admin level each segment belongs to. See `docs/pages/explanation/package_lines.md`.
- **package**: runs `package-polygons`, `package-points`, and `package-lines` against one input in a single call, for the common case of wanting the full cartographic bundle at once. See `docs/pages/explanation/package.md`.
- **edge-match**: `assign-one` (default, forcing the whole input file onto one majority-vote parent; opt into per-child `assign-many` via `--multi-parent` for files whose children genuinely scatter across multiple parents, see `docs/adr/0082`) → per-group `edge-extend` (own subprocess) → batched `edge-clip` → `edge-stitch`, fitting a child layer into a coarser parent/clip layer (e.g. admin4 into admin0). The children role MAY span multiple raw files per call, combined via a memory-bounded per-file `inputs`+`assign` loop, groups/clip/stitch/outputs running once over the combined result so cross-file children sharing a parent extend together (`--multi-parent`/`step` rejected outright for a multi-file call, see `docs/adr/0084`). Also accepts an opt-in `--merge` (a plain boolean, plus `--parent-include`/`--parent-exclude`/`--child-include`/`--child-exclude`/`--prefer` narrowing flags, the same design `edge-mosaic` uses), which both groups every child with no parent overlap at all into one orphan group of its own (sentinel `PASSTHROUGH_PARENT_FID`), extending it like any other group and keeping it unclipped in the output (materially weaker safety profile than `edge-mosaic`'s own child passthrough, see `docs/adr/0081`), and gap-fills a parent matched by zero children via the shared `fill_unmatched_parents()` helper, identically to `edge-mosaic` (see `docs/adr/0088`). See `docs/pages/explanation/edge_match.md`.
- **edge-mosaic**: `assign-one` → `edge-clip` → `edge-stitch`, fitting an already-extended child layer (a prior `edge_extend()` output) into a new/different parent/clip layer, skipping Voronoi extension entirely. See `docs/pages/explanation/edge_mosaic.md`.
- **topo-clean**: `topo-detect` → fixes the reported coverage defects (gaps, overlaps) with `ST_CoverageClean`, reporting the fix outcome in the issues file for manual review. See `docs/pages/explanation/topo_clean.md`.
- **change**: compares an old/new polygon layer pair and classifies every unit (unchanged/renamed/modified/relocated/split/merge/complex/created/removed) via spatial overlap and optional code/name identity linking; writes a tabular changelog plus a colored spatial overlay layer. See `docs/pages/explanation/change.md`.
- **schema-map**: maps a source-column → target-schema crosswalk by inferring the admin hierarchy structurally (cardinality/containment, never column names) and classifying code vs. name by value shape, deterministically, no LLM; never renames anything itself. See `docs/pages/explanation/schema_map.md`.
- **schema-refactor**: renames/drops columns per a crosswalk from `schema-map` (likely hand-edited first). See `docs/pages/explanation/schema_refactor.md`.
- **schema-crosswalk**: `schema-map` → `schema-refactor`, in one call, so a user can see mapped values right away and iterate by hand-editing the written crosswalk and re-running `schema-refactor` on it. See `docs/pages/explanation/schema_crosswalk.md`.
- **schema-fill**: stamps a new `adm_lvl` column (overridable via `--depth-column`) with each row's real depth, then cascades each admin-hierarchy column down to that depth, pinned per row so a genuine NULL at a row's own real depth is never backfilled from a shallower ancestor; levels derived structurally by default, or via an explicit `--name-field`/`--code-field` pair; run against an already-clipped/stitched layer, then `package-polygons` to dissolve every level normally. See `docs/pages/explanation/schema_fill.md`.
- **code-refactor**: cold-starts a hierarchical code on a flat, finest-level input, levels resolved structurally by default (or via an explicit `--name-field`/`--code-field` pair), each level's units ranked under their parent and assigned a fresh sequential code in a configurable `--root-code`/`--delimiter`/`--min-width` format (`core.code`, a shared leaf). See `docs/pages/explanation/code_refactor.md`, `docs/pages/explanation/code.md`.
- **code-update**: reconciles an already-coded OLD layer against an uncoded NEW candidate, classifying every unit via `core.change`'s own engine and applying a changelog-driven retention policy (retain/replace/retire) per unit, cascading a changed parent's new code prefix down to every unchanged/renamed descendant. Format (`root_code`/`delimiter`/`min_width`) auto-detects off OLD's own existing codes unless overridden. See `docs/pages/explanation/code_update.md`, `docs/pages/explanation/code.md`.

## Deployment Targets

The pipeline targets two memory-constrained environments: **DuckDB-WASM in
the browser** (no disk, JS heap only, and the Python pipeline documents the SQL
approach for eventual JS/TS porting) and **memory-limited containers**
(typically 2–4 GB RAM, no swap; pip-install this package into whatever image
you need, no Dockerfile ships here). Prefer approaches that minimize
intermediate materializations, avoid platform-specific calls (`os.sysconf`,
`/proc`, `subprocess`), and work with small buffer budgets.

## Architecture

Each tool's pipeline is a sequence of stages, each a standalone module in its
own `topo_tools/core/{tool}/` package. All stages of one `edge_extend()`/
`edge_match()` call share a single file-backed DuckDB connection; tables are
the IPC mechanism between stages (per-group subprocesses inside `edge-match`
are the one exception, see `docs/pages/explanation/edge_match.md`). Three layers,
each with a specific job (mirroring `geoparquet-io`'s `core`/`api`/`cli`
split):

- `topo_tools/core/{edge_extend,assign,edge_clip,edge_stitch,topo_detect,dissolve,schema_fill,package_polygons,package_points,package_lines,edge_match,edge_mosaic,topo_clean,change,code_refactor,code_update}/`:
  stage implementations. `core.edge_match`/`core.edge_mosaic` call
  `core.edge_clip`/`core.edge_stitch` stage functions directly (not through
  their own `api.*()`), the same pattern `core.edge_match` uses to call
  `core.edge_extend`'s stage functions directly, `core.topo_clean` uses to
  call `core.topo_detect`'s issue-detection stage function directly (see
  `docs/adr/0028`), `core.package_polygons`/`core.package_points`/
  `core.package_lines` use to call `core.dissolve`'s stage functions
  directly, once per detected admin level, and `core.code_update` uses to
  call `core.dissolve`'s, `core.change`'s, and `core.assign`'s stage
  functions directly (see `docs/adr/0103`). `core.assign` has no
  `api.*()`/CLI pipeline of its own, so it's called one layer up instead,
  directly from `api.edge_mosaic`/`api.edge_clip`/`api.edge_match`/
  `api.code_update`. `core.assign`/`core.edge_clip`/`core.edge_stitch`/
  `core.topo_detect`/`core.dissolve`/`core.code` are themselves neutral
  leaves, alongside `core.constants`/`core.coverage`/`core.io`/
  `core.duckdb_utils`/`core.units`; every tool package may import any of
  these eleven, none of them may import back, except `core.dissolve`'s one
  narrow, explicit carve-out below. `core.schema_map` is not a neutral leaf
  but MAY be imported by `core.schema_fill`, `core.dissolve`,
  `core.package_polygons`, `core.package_points`, `core.package_lines`,
  `core.code_refactor`, and `core.code_update` specifically (the
  `name_field`/`code_field`/level-detection mechanism,
  `core/schema_map/_levels.py`, `core/schema_map/_level_columns.py`), never
  the reverse (see `docs/adr/0075`,
  `docs/adr/0092`); `schema-fill` does not call `core.dissolve` itself, a
  caller runs `package-polygons` separately after filling (see
  `docs/pages/explanation/schema_fill.md`).
- `topo_tools/api/{edge_extend,edge_clip,edge_stitch,topo_detect,schema_fill,package_polygons,package_points,package_lines,package,edge_match,edge_mosaic,topo_clean,change,code_refactor,code_update}.py`:
  public API functions; each chains its own tool's stages for exactly one
  file (or file pair) per call, except `edge-mosaic`'s and `edge-match`'s
  children roles, which MAY span multiple files (see
  `docs/pages/reference/edge_mosaic.md`, `docs/pages/reference/edge_match.md`).
  `edge-clip` is a strict one-children-file/one-parent-file/one-output
  primitive (see `docs/adr/0080`).
- `topo_tools/cli/main.py`: the click CLI, mapping flags/env vars onto one
  `api.*()` call per invocation, one file (or pair) at a time, except
  `edge-mosaic`'s and `edge-match`'s child arguments (MAY be a glob pattern)
  and their `--input` options (repeatable, comma-splittable), no directory
  batching.

Import boundaries between these layers, and between tools, are mechanically
enforced by `pyproject.toml`'s import-linter contracts, see
`docs/pages/reference/shared.md` for the MUST/MAY rules.

### Pipeline, Configuration & Table Naming

Each tool's stages are numbered modules in its own `topo_tools/core/{tool}/`
package (`_01_...py`, ...), each with its own docstring; behavior contracts
live in `docs/pages/reference/{tool}.md`, stage-by-stage detail in
`docs/pages/explanation/{tool}.md`.

Settings flow in as plain keyword arguments on each tool's own `api.*()`
function, mapped 1:1 from CLI flags/env vars. There's no module-level `argparse`/env
parsing anywhere. Common settings (`tmp_dir`, `threads`, `overwrite`,
`debug`, `step`) are in `docs/pages/reference/shared.md`; per-tool
paths/arguments/`step` values are in `docs/pages/reference/{tool}.md`. Pure
literals live in `topo_tools/core/{tool}/_constants.py` and
`topo_tools/core/constants.py`.

Tables are named `{name}_{stage}[suffix]`: no suffix means one persistent
table; a letter suffix (`_03a`, `_03b`) means multiple and **all** get a
letter, never one left bare; `_tmp{n}` is dropped before the function
returns, invisible unless `--debug`. Each tool uses its own `name` (e.g.
`{input}_edge_match`) so tools never collide on the same input/`tmp_dir`;
per-tool table names are in `docs/pages/explanation/{tool}.md`.

### Key Patterns

- **DuckDB spatial extension** handles all geometry operations (`ST_*` functions), one file-backed connection per input file (`topo_tools/core/duckdb_utils.py`), returned as a `ProfiledConnection` proxy that logs timing/memory per query when `--debug` is set.
- **DuckDB tables as IPC**: stages read and write named tables on the shared connection; no Parquet between stages.
- **Topology validation** (`check_valid_topology()` in every tool's outputs stage, chaining `check_invalid_edges`/`check_gaps`, backed by `has_invalid_edges`/`has_gaps` in `topo_tools/core/coverage.py`) always unnests MultiPolygons first. No byte-exactness check, see the next bullet.
- **`has_gaps()`/`check_valid_topology()` default `gap_maximum_width` to `SNAP_TOLERANCE` (GEOS's own `CoverageCleaner` parameter name, see `docs/adr/0002`), tolerating a wider gap**: a wider leftover gap may be a real hole in the parent/clip layer's own shape (e.g. Lesotho inside South Africa), a real unfilled-by-design gap, or a real unbatched absence, not a defect, so `edge-match`/`edge-mosaic`/`topo-clean`/`edge-stitch` all rely on this default and report any such gap as a `kind='gap'` row in the issues report instead of raising (see `docs/adr/0035`, `docs/adr/0037`, `docs/adr/0038`, `docs/adr/0039`). `edge-extend` is the one outlier, passing `gap_maximum_width=0` explicitly for its zero-tolerance check: it has no parent/clip layer, so any gap in its own coverage is unambiguously a bug. `topo-clean`/`edge-match`/`edge-mosaic`/`edge-stitch` share one issues-table column schema and skip writing the file entirely when it would be empty (see `docs/adr/0035`, `docs/adr/0036`).
- **Geometry column names**: `geom` in DuckDB tables, `geometry` in final output. `duckdb_memory()` profiling caveats are in `docs/pages/explanation/performance.md`.
- **`core.io.read_and_reproject()` raises `ValueError` on invalid source geometry `ST_MakeValid` can't repair, and on a 0-row read.** A 0-row read is a known DuckDB-spatial-bundled-GDAL gap on some real FileGDBs that a system-installed GDAL reads fine; re-export via `gdal vector convert` to GeoParquet/GPKG first as the workaround (see `docs/adr/0053`).
- **`_05_merge.py` joins against nearby originals via bbox-prefiltered, part-exploded join, never a global `ST_Union_Agg` operand** (`_02_lines.py`'s neighbor-union join and `_03_points.py`'s shared-boundary-zone difference both use whole-fid bboxes instead, not interchangeable with part-exploded). `_03_points.py` raises if its differencing drops a fid entirely, and `_06_outputs.py` raises if the extended geometry no longer covers its original footprint (`SNAP_TOLERANCE`-buffered `ST_Covers`). See `docs/adr/0001`, `docs/adr/0090`.
- **Never call `ST_XMin`/`ST_XMax`/`ST_YMin`/`ST_YMax` inline inside a JOIN's `ON` clause**, can hang indefinitely on high-vertex-count tables. Precompute bbox columns on the joined table/CTE first, as `_05_merge.py` does (see `docs/adr/0014`).
- **`_04_voronoi.py` clips a Voronoi cell to valid WGS84 range (`-180/-90/180/90`) only when that cell's own bbox already exceeds it**, leaving every interior cell byte-identical to its unclipped geometry. A peripheral boundary point's cell is mathematically unbounded; GEOS closes it using an auto-sized envelope based on the whole point cloud's own extent, which overshoots valid range for a country-scale point cloud with a remote exclave or polar-adjacent territory (e.g. Chile's Isla de Pascua/Antártica Chilena, Indonesia's eastern Papua group). Clipping the whole raw diagram as one blob before the per-cell dump OOM's on Chile-scale input; clipping every cell unconditionally perturbs even well-within-bounds cells enough to break `edge-match`'s coverage-clean step. See `docs/adr/0096`.
- **Byte-exact preservation of original polygon vertices is not a goal.** `ST_CoverageClean` may shift any polygon's boundary, including previously-untouched ones (see `docs/pages/explanation/topology.md`).
- **`edge-match` reuses `edge-extend`'s stage functions per-group, each in an isolated subprocess** (GEOS's native heap isn't fully released between files). Two subprocess generations per call: per-group `edge-extend`, then a separate batched `edge-clip` pass (see `docs/adr/0020`, `docs/pages/explanation/edge_match.md`).
- **`edge-mosaic` skips Voronoi extension entirely**, assuming the child layer is already a finished `edge_extend()` output; chains `assign-one` → `edge-clip` → `edge-stitch` directly, no per-group subprocess. `edge-mosaic` also accepts an opt-in `--merge` (a plain boolean, plus `--parent-include`/`--parent-exclude`/`--child-include`/`--child-exclude`/`--prefer` narrowing flags), which both keeps a parent matched by zero children in the output unclipped (using the parent's own geometry, via the shared `fill_unmatched_parents()` helper) and keeps a whole unmatched child file unclipped in the output, coupled with copying named parent columns onto every matched child; `edge-match` performs the identical pair of behaviors (see `docs/adr/0088`); `edge-clip` has no equivalent, since only `edge-mosaic`'s children are guaranteed to already be a complete coverage layer (see `docs/adr/0079`, `docs/adr/0083`, superseding `docs/adr/0078`'s child-orphan passthrough). See `docs/pages/explanation/edge_mosaic.md`. With more than one input file, `edge-mosaic` assigns/clips one children file at a time against a cached parent-tile decomposition (the memory-safe pattern standalone `edge-clip` used before it reverted to a strict 1:1 primitive, see `docs/adr/0079`, `docs/adr/0080`).
- **`core/edge_clip/`'s `_engine.main()` clips one `parent_fid` at a time, each in its own subprocess, boundary adaptively grid-tiled**, uniformly for every caller including `edge-match`; a bad `parent_fid` aborts the whole run. Tile size derives from each parent's own vertex density (small parents skip tiling) (see `docs/adr/0015`, `docs/adr/0016`, `docs/adr/0017`).
- **Standalone `edge-clip` never expects `parent_fid` on its input**; it always assigns internally via `assign-one` (`api.edge_clip.clip()` calling `core.assign.load_children`/`load_parent`/`assign_one` directly, no local wrapper) before clipping, no strategy flag. `edge-match`/`edge-mosaic` are unaffected, they call `core.edge_clip._engine.main()` directly with their own already-tagged tables (see `docs/adr/0021`).
- **Standalone `edge-clip` is a strict one-children-file/one-parent-file/one-output primitive**; batching many children files against one shared parent load moved to `edge-mosaic` once it adopted the same memory-safe per-file-loop pattern (see `docs/adr/0080`, superseding `docs/adr/0022`/`docs/adr/0023`/`docs/adr/0024`). Its per-parent-fid subprocess working directory (`core/edge_clip/_engine.py`) is always cleared before use regardless of `--debug`, since two callers can land on the same `parent_fid` and collide on a leftover catalog otherwise (see `docs/adr/0025`).
- **Any manually-declared DuckDB table schema fed by `bbox_columns_sql()` MUST insert `BY NAME`, never positionally.** `bbox_columns_sql()`'s emitted column order (`xmin, xmax, ymin, ymax`) doesn't have to match a hand-written `CREATE TABLE`'s order, and a positional insert won't catch a mismatch, it silently swaps values (see `docs/adr/0026`).
- **`core/assign/`'s `assign-one` (per-file majority vote, forcing every child in a file onto its winner unconditionally once one exists) is the default for both `edge-mosaic` and `edge-match`.** `assign-many` (per-child plurality, dropping a zero-overlap child individually) is an `edge-match`-only opt-in (`--multi-parent`), for files whose children genuinely scatter across multiple parents (e.g. a poorly-digitized admin4 layer). A child forced onto its file's winner with zero individual overlap is not dropped at assign time; it still gets clipped and MAY drop later at clip time if its result is empty, reported as a `kind='clip-empty'` issue row (see `docs/pages/explanation/assign.md`, `docs/adr/0019`, `docs/adr/0082`).
- **`core.topo_clean` depends only on the shared leaf modules and `core.topo_detect`, not `core.edge_extend`.** `topo-clean`'s issue detection was extracted into its own standalone `topo-detect` tool, the same primitive-extraction pattern as `assign`/`edge_clip`/`edge_stitch`; `topo_clean` calls `core.topo_detect`'s stage function directly (see `docs/adr/0028`, `docs/pages/explanation/topo_clean.md`, `docs/pages/explanation/topo_detect.md`).
- **`ST_CoverageClean`'s `gap_maximum_width` has no GEOS-native auto-fill default.** `topo-clean`'s `--gap-width auto` mode computes an explicit width from the widest thin detected gap; `all` mode uses a fixed `GAP_MAXIMUM_WIDTH_ALL_DEG = 360` sentinel (see `docs/adr/0002`).
- **`coverage_clean()` (`core/coverage.py`) must call `ST_CoverageClean` positionally, never via DuckDB's `:=` named-argument syntax.** DuckDB binds named arguments to compiled/extension scalar functions purely by position, silently discarding the name (see `docs/adr/0003`).
- **`edge-stitch`'s `_02_clean` stage calls `coverage_clean_escalating()`, not `coverage_clean()` directly**, widening `snapping_distance` past `SNAP_TOLERANCE` one `SNAP_ESCALATION_STEP` at a time (up to `SNAP_ESCALATION_MAX_STEPS`) only if invalid edges remain after the first pass; every other `coverage_clean()` call site is unaffected (see `docs/adr/0089`, `docs/pages/explanation/edge_stitch.md`).
- **`ST_Distance(GEOMETRY, GEOMETRY)` is unreliable for two disjoint polygons at small separations.** Use `ST_XMin`/`ST_XMax`/`ST_YMin`/`ST_YMax` extent comparisons or `ST_MaximumInscribedCircle` instead (see `docs/adr/0004`).
- **`topo_detect/_02_issues.py`'s per-detection-kind retry falls back to an empty result table (logged) if both attempts fail, rather than leaving the table missing.** Any new call site of `_detect_or_empty` must supply `empty_sql` (see `docs/adr/0005`).
- **`change`'s classification runs in Python (`core/change/_03_classify.py`), not SQL**, feature-count-scaled, not vertex-scaled, unlike `edge-extend`/`topo-clean`'s work. See `docs/pages/explanation/change.md`.
- **`change` always uses exact `ST_Intersection`, never point-sampling**, unlike the sister JS app's WASM-only-bug workaround. See `docs/pages/explanation/change.md`.
- **`topo-clean`'s `--maximum-gap-width`/`--snapping-distance` are decimal degrees, not meters** (`_01` is always EPSG:4326). See `docs/pages/explanation/topo_clean.md`.
- **A read-role file argument MAY be an `http://`/`https://` URL to a `.parquet` file**, resolved via `core.io.resolve_input_path()`/`input_basename()`, never plain `Path()` (which mangles a URL's `//`); output-role arguments always stay local paths (see `docs/adr/0043`).
- **`schema-crosswalk` reuses `schema-map`'s and `schema-refactor`'s stage functions directly rather than re-implementing matching or renaming**, the same primitive-reuse pattern as `topo-clean`/`topo-detect` (`docs/adr/0028`), but split across two independent `name` sub-namespaces (`{name}` for `schema-map`'s tables, `f"{name}_apply"` for `schema-refactor`'s) since both hardcode `"{name}_02"` for different data. The apply namespace's `_01` table is a DuckDB **view** over the already-loaded input, not a copy, per this project's memory-constrained deployment targets; it MUST be dropped before any `DROP TABLE IF EXISTS` targets that name, since DuckDB raises a Catalog Error dropping a view as a table even with `IF EXISTS`. See `docs/pages/explanation/schema_crosswalk.md`.
- **`schema-fill`/`package-polygons`/`package-points`/`package-lines`/`package` all detect every hierarchy level structurally by default (`core.schema_map`'s cardinality/containment matcher, no naming convention assumed), never a hardcoded column-naming convention or column count**, or via an explicit `name_field`/`code_field` pair (`--name-field`/`--code-field`, given together or not at all). Structural auto-detection groups each level's columns by a shared naming anchor (`_level_anchors()`, `core/schema_map/_level_columns.py`): the text every level's own code column shares with every other level's, as a common prefix and (of what's left) a common suffix, so the differing middle part (a digit like `1`/`2`/`3`, or a whole word like `state`/`county`) can anchor a sibling column at either end (`is_level_identity_column()`), never assuming a digit or a fixed position. `schema-fill` stamps a depth column (`adm_lvl` by default, overridable via `depth_column`/`--depth-column`) from the *original* (pre-fill) code columns so a caller can tell a genuine leaf-depth row from one only ever filled down; every level past a row's own stamped depth is pinned to that row's own value at (or nearest below) that depth, per row, never a shared file-wide level, so a genuine NULL at a row's own real depth is left untouched rather than backfilled from a shallower ancestor (see `docs/adr/0075`, `docs/adr/0093`); `package-polygons`'s own unmodified per-level `core.dissolve` call then carries the depth column through automatically via its existing auto-keep-constant-column behavior.
- **`package-polygons`/`package-points`/`package-lines` reuse `core.dissolve`'s stage functions directly rather than re-implementing aggregation**, the same primitive-reuse pattern `edge-match` uses on `edge-extend` (see `docs/pages/explanation/package_polygons.md`, `docs/pages/explanation/package_points.md`, `docs/pages/explanation/package_lines.md`).
- **`core.code`'s next-available integer per parent is derived only from codes live in the current run, never a persisted registry.** `code-update` seeds it with that level's own just-computed retained (`unchanged`/`renamed`) set, so a code retired this run (a `merge`'s old codes, a `removed` unit's code) may be immediately reused by an unrelated new/split/merge/created unit at the same level, same run; a code removed in an earlier run is not tracked at all (see `docs/adr/0102`, `docs/pages/explanation/code.md`).

### Supported Formats

Input/output: GeoParquet (`.parquet`), GeoPackage (`.gpkg`), Shapefile (`.shp`), GeoJSON (`.geojson`). Output format matches input format.

## Commands

```bash
# Install dependencies
uv sync

# Run the edge-extend tool (processes exactly one file per call)
uv run topo-tools edge-extend example.geojson
# equivalently: uv run python -m topo_tools edge-extend example.geojson

# Run the edge-match tool (fits a child layer into a parent/clip layer)
uv run topo-tools edge-match children.geojson parents.geojson

# Run the edge-mosaic tool (re-clips an already-extended child layer into a new parent layer)
uv run topo-tools edge-mosaic extended_children.parquet new_parents.geojson

# Run edge-clip/edge-stitch/topo-detect standalone (the primitives edge-match/edge-mosaic/topo-clean chain internally)
uv run topo-tools edge-clip children.parquet parents.geojson
uv run topo-tools edge-stitch tiled.geojson
uv run topo-tools topo-detect example.geojson

# Run the schema-fill tool (fill down admin columns, stamp each row's real depth)
uv run topo-tools schema-fill admin4.geojson

# Run the package-polygons tool (dissolve into every detected coarser admin level)
uv run topo-tools package-polygons admin3.geojson

# Run the package-points/package-lines tools (label points / deduplicated boundary lines)
uv run topo-tools package-points admin3.geojson
uv run topo-tools package-lines admin3.geojson

# Run the package tool (package-polygons + package-points + package-lines in one call)
uv run topo-tools package admin3.geojson

# Override auto-detected level naming with an explicit pair (any tool above)
uv run topo-tools package-polygons admin3.geojson --name-field adm{n}_name --code-field adm{n}_pcode

# Run the topo-clean tool (topo-detect, then fix gaps+overlaps, reporting the outcome in the issues file)
uv run topo-tools topo-clean example.geojson

# Run the change tool (compares an old/new polygon layer pair)
uv run topo-tools change old.geojson new.geojson

# Run schema-map/schema-refactor standalone (propose a crosswalk, then apply it separately)
uv run topo-tools schema-map example.geojson
uv run topo-tools schema-refactor example.geojson example_crosswalk.csv

# Run the schema-crosswalk tool (schema-map + schema-refactor in one call)
uv run topo-tools schema-crosswalk example.geojson

# Run the code-refactor tool (cold-start a hierarchical code, ranked per parent)
uv run topo-tools code-refactor admin2.geojson --root-code AFG --delimiter . --min-width 3

# Run the code-update tool (reconcile an already-coded OLD layer against an uncoded NEW candidate)
uv run topo-tools code-update admin1_old.geojson admin1_new.geojson

# Format and lint
uv run ruff format && uv run ruff check
```

Pre-commit hooks run `uv-sync`, `ruff-format`, and `ruff-check` automatically.

## Test Datasets

| Dataset | Use |
| --- | --- |
| **West Africa cluster** (`sen`/`gmb`/`gnb`/`gin`/`civ`/`gha`/`tgo`/`ben`, portolan `adm2`) | Mutually neighboring countries, used for single-file tool tests (edge-extend/edge-match/topo-clean/change) and edge-mosaic's and edge-match's multi-file combine tests |

A full portolan catalog (real, large-scale admin boundary data, multiple
countries and admin levels, some with multiple historical versions) is
available for at-scale/real-data stress testing beyond the cluster above:

- **Local copy**: `/Users/computer/GitHub/OCHA-DAP/hdx-scraper-cod-ab-global/portolan`
- **Live/canonical source**: [source.coop/hdx/cod-ab](https://source.coop/hdx/cod-ab),
  STAC root catalog at `https://data.source.coop/hdx/cod-ab/catalog.json`
  (`id: portolan`; per-country `child` links, e.g. `./chl/catalog.json`)

**HARD RULE: the portolan catalog (local copy or live source) is read-only.**
Never write, modify, move, or delete anything inside
`/Users/computer/GitHub/OCHA-DAP/hdx-scraper-cod-ab-global/portolan`. No
`--output-path`/`--overwrite`, no `--tmp-dir`, no `--debug` exports, nothing.
Only ever read from it. Every output/tmp/debug path for a portolan-sourced
test run must point outside the catalog (e.g. the session scratchpad or
`/tmp`).

See the `at-scale-testing` skill for the STAC layout and how to pick a
file (or an old/new comparison pair, for `change`) from the catalog.

## Reference Docs

- `docs/pages/tutorials/{tool}.md`: GDAL-style getting-started examples per tool
- `docs/pages/reference/{tool}.md`: behavior contract per tool (`shared.md` for common settings/gates)
- `docs/pages/explanation/{tool}.md`: stage-by-stage detail for `edge_extend`, `topology`, `assign`, `edge_clip`, `edge_stitch`, `topo_detect`, `edge_match`, `edge_mosaic`, `topo_clean`, `change`, `schema_map`, `schema_refactor`, `schema_crosswalk`, `schema_fill`, `package_polygons`, `package_points`, `package_lines`, `package`, `code`, `code_refactor`, `code_update`; notable: `topology.md` has the SPATIAL_JOIN memory bug, `performance.md` has thread-scaling benchmarks + the RTREE experiment, `voronoi-memory.md` has per-file resampling distance and memory ceilings for `phl_admin3`/`idn_admin3`, `edge_match.md` has the `check_gaps` caveat
- `docs/`: a Zensical site (published to GitHub Pages by `.github/workflows/docs.yml`), rooted at `docs/` with content under `docs/pages/`; `docs/adr/` sits outside the site's content tree, unpublished
- `.claude/skills/`: `publishing` (PyPI release via OIDC), `verify-duckdb-function` (DuckDB/spatial function lookup), `at-scale-testing` (portolan catalog layout, picking a test file/pair), `manual-dev-testing` (running any tool against your own data)
- `docs/adr/README.md`: how to decide ADR vs. `docs/pages/explanation/` vs. CLAUDE.md's Key Patterns; `docs/adr/` itself holds the decision records
