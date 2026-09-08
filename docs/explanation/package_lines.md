# Package-Lines Explanation

`package-lines` produces one deduplicated line network of admin
boundaries (shared between two units, or exterior to all of them), tagged
by adjacency and the coarsest admin level each segment belongs to. A web
map can style or filter international vs. sub-national boundaries from
this one layer, instead of drawing every level's own polygon outline on
top of each other.

## Usage

```sh
topo-tools package-lines admin3.geojson --target-schema schema.yaml
```

```python
from topo_tools import package_lines

package_lines("admin3.parquet", target_schema_path="schema.yaml")
```

`OUTPUT_FILE` (positional, optional) defaults to `INPUT_FILE` with a
`_lines` suffix.

Run `topo-tools package-lines --help` for the full, always-current option
list.

## Why not `ST_SharedPaths`

PostGIS exposes `ST_SharedPaths` for exactly this shared-boundary
extraction. This project's DuckDB spatial build has no equivalent
function; `docs/how-to/verify-duckdb-function.md`'s live catalog lookup
confirms `ST_SharedPaths` and `ST_Relate` are both absent. `package-lines`
instead builds shared boundaries from `ST_Boundary` plus `ST_Intersection`
plus `ST_CollectionExtract`, verified end to end against synthetic
geometry during design (adjacent squares, a three-in-a-row middle unit, a
multi-part/archipelago fid, and a corner-only touch).

## Pipeline (`_02_boundaries`)

1. Dissolve the input once, at the finest detected level only (via
   `core.dissolve`'s `_02_dissolve.main()`); every coarser boundary is
   already contained in the finest level's own adjacency, so no per-level
   repeat is needed. Every ancestor code column survives as a
   constant-per-group attribute, used later for classification.
2. Build a part-exploded bbox table (`UNNEST(ST_Dump(geom))`, bbox columns
   precomputed via `bbox_columns_sql()`, never inline inside a JOIN's `ON`
   clause), so a multi-part fid with a remote exclave doesn't make every
   candidate-pair bbox comparison span the whole fid's extent.
3. Find candidate touching fid pairs from bbox overlap at the part level
   (`DISTINCT`, `a.fid < b.fid`), then confirm real adjacency with
   `ST_Touches` against each pair's whole-fid geometry (a part-level bbox
   overlap doesn't guarantee the whole fids actually touch).
4. For each touching pair, compute the shared segment as
   `ST_LineMerge(ST_CollectionExtract(ST_Intersection(boundary_a,
   boundary_b), 2))`, filtering out `NULL`/empty results; a corner-only
   touch has `ST_Touches` true but an empty intersection, and is filtered
   out here, producing zero shared rows for that pair. `ST_LineMerge` is
   required even when both sides' vertices exactly coincide along the
   shared edge: `ST_Intersection` on two boundaries returns one
   `LineString` fragment per matching edge segment, not one merged line,
   so real admin boundaries with many vertices along a shared border
   produce hundreds of tiny fragments without it (see `docs/adr/0097`).
5. Union each fid's own shared segments (both sides of every pair it's in)
   via `ST_Union_Agg`, then compute its exterior as
   `ST_LineMerge(ST_Difference(boundary, own_shared))`, dumped to atomic
   `LineString` rows. A fid with two disjoint exterior segments (e.g. one
   touching side, one fully remote part) produces two rows, never one
   `MultiLineString`.
6. Dump shared segments to atomic `LineString` rows too (a multi-part
   fid's shared adjacency can itself be a `MultiLineString`), then classify
   every row: a shared row's depth is the coarsest detected level at which
   its two sides' own code columns first differ; an exterior row's depth
   is always the coarsest detected level, since the exterior ring is
   identical regardless of grouping.
7. Raise `ValueError` if any finest-level fid is absent from every output
   row (as `left_fid` or `right_fid`), catching a fid silently dropped
   somewhere in the pipeline. A fid fully enclosed by neighbors (zero
   exterior boundary) can only ever appear as `right_fid`, since candidate
   pairs are generated with `a.fid < b.fid`; the check accepts either
   column, not `left_fid` alone.

`depth_column`/`--depth-column` is checked up front against the tool's own
fixed output column names (`left_fid`, `right_fid`, `boundary_type`,
`geom`), raising `ValueError` on a collision rather than letting
DuckDB silently rename the duplicate.

## Portolan-scale profiling

The real target scale for this tool, `--debug` off, Apple Silicon/10 logical
cores:

| Run                              | Fids in / shared+exterior rows out | Wall time | RSS peak | Result                              |
| --------------------------------- | ---------------------------------- | --------- | -------- | ------------------------------------ |
| Global admin4 (`portolan/global/admin4/admin4.parquet`, 217,223 rows, `--depth-column pkg_lvl`) | 217,223 / 612,006 shared + 44,356 exterior | 333s | 7.74 GB | Every finest-level fid present in the output |

The bbox-prefiltered candidate-pair join stays close to linear in input
size in practice: touching pairs cluster within each country's own
landmass, so a global run costs roughly the sum of each country's own
candidate-pair search, not a combinatorial blow-up across all 217,223 rows
at once.
