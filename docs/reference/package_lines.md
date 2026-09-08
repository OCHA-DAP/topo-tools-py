# package-lines

See `docs/reference/README.md` for the MUST/SHOULD/MAY convention, and
`docs/reference/shared.md` for rules `package-lines` shares with other
tools.

## Inputs

- `package-lines` MUST read the input and reproject it to EPSG:4326.
- `package-lines` MUST detect every admin level present via a
  target-schema YAML, raising `ValueError` if no level is found.

## Boundary extraction

- `package-lines` MUST dissolve the input once, at the finest detected
  level only; every coarser boundary is already contained in that level's
  own adjacency, so no per-level repeat dissolve is needed.
- `package-lines` MUST derive each pair of touching units' shared boundary
  from `ST_Boundary` and `ST_Intersection`, never a PostGIS-style
  shared-paths function (not available in this DuckDB spatial build), and
  MUST merge the result with `ST_LineMerge` before dumping to atomic rows:
  an unmerged intersection returns one fragment per matching edge segment,
  not one line, even where both sides' vertices exactly coincide.
- A shared-boundary row MUST be produced exactly once per touching pair
  (`left_fid < right_fid`), never twice. A pair whose polygons only touch
  at a point (corner touch) MUST produce zero shared rows.
- `package-lines` MUST dump every multi-part shared or exterior geometry
  into atomic `LineString` rows; a unit with multiple disjoint exterior
  segments MUST produce one row per segment, never a single
  `MultiLineString`.
- Every output row MUST carry a `boundary_type` of `shared` or `exterior`.
  `right_fid` MUST be `NULL` on every exterior row.
- `package-lines` MUST classify every shared row by the coarsest detected
  level at which its two sides' code columns first differ, and every
  exterior row by the coarsest detected level, into a depth column
  (`adm_lvl` by default, overridable via `depth_column`).
- `package-lines` MUST raise `ValueError` if any finest-level unit is
  absent from every output row (as `left_fid` or `right_fid`).
- `package-lines` MUST raise `ValueError` if `depth_column` collides with
  one of its own fixed output column names (`left_fid`, `right_fid`,
  `boundary_type`, `geom`).

## Outputs

- `package-lines` performs no topology hard gate; it is a derived
  cartographic layer, not a coverage layer.
- `package-lines` MUST combine shared and exterior rows from every level
  into one output file, deduplicated so no boundary segment repeats across
  levels.

## Configuration (`api.package_lines.package_lines()` / CLI)

- `package-lines` MUST process exactly one input file per call.
- The output path MUST default to the input path with a `_lines` suffix.
- `package-lines` MUST raise `FileExistsError` if the output path already
  exists and overwriting wasn't requested.
- `step`, if given, MUST be one of `inputs`, `boundaries`, `outputs`; any
  other value MUST raise `ValueError`.
- `target_schema_path`, if omitted, MUST default to the bundled generic
  target schema.
