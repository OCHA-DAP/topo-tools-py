# package-points

See `docs/reference/README.md` for the MUST/SHOULD/MAY convention, and
`docs/reference/shared.md` for rules `package-points` shares with other
tools.

## Inputs

- `package-points` MUST read the input and reproject it to EPSG:4326.
- `package-points` MUST detect every admin level present, either
  structurally (`core.schema_map`'s cardinality/containment matcher, no
  naming convention assumed, the default when `name_field`/`code_field`
  are omitted) or via an explicit `name_field`/`code_field` pair, raising
  `ValueError` if no level is found.

## Point extraction

- `package-points` MUST dissolve the input once per detected level,
  grouping by that level's own code column, then reduce each dissolved
  unit to a single point via `ST_MaximumInscribedCircle(geom).center` (the
  pole of inaccessibility), never the centroid.
- `package-points` MUST raise `ValueError` if a level's dissolved row count
  does not equal that level's distinct code-column count in the input, or
  if any output point is not covered by its own source polygon
  (`ST_Covers`).
- Every level's points MUST be tagged with a depth column (`adm_lvl` by
  default, overridable via `depth_column`), holding that level's own
  numeric depth. `package-points` MUST raise `ValueError` if `depth_column`
  already exists as a column on the input, rather than silently producing
  a renamed duplicate column.

## Outputs

- `package-points` performs no topology hard gate; it is a derived
  cartographic layer, not a coverage layer.
- `package-points` MUST combine every level's points into one output file.
  Coarser levels carry fewer columns than finer ones (every finer-level
  column is absent, not null); the combine MUST NOT assume a fixed column
  set across levels.

## Configuration (`api.package_points.package_points()` / CLI)

- `package-points` MUST process exactly one input file per call.
- The output path MUST default to the input path with a `_points` suffix.
- `package-points` MUST raise `FileExistsError` if the output path already
  exists and overwriting wasn't requested.
- `step`, if given, MUST be one of `inputs`, `points`, `outputs`; any
  other value MUST raise `ValueError`.
- `name_field`/`code_field` MUST be given together, or both omitted; when
  both are omitted, `package-points` MUST fall back to full structural
  auto-detection of every level.
