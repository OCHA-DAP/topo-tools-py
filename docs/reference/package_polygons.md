# package-polygons

See `docs/reference/README.md` for the MUST/SHOULD/MAY convention, and
`docs/reference/shared.md` for rules `package-polygons` shares with other
tools.

## Inputs

- `package-polygons` MUST read the input and reproject it to EPSG:4326.
- `package-polygons` MUST detect every admin level present via a
  target-schema YAML (the same format `schema-map`/`schema-fill` use),
  raising `ValueError` if no level is found.

## Dissolving

- `package-polygons` MUST dissolve the input once per detected level
  coarser than the finest, grouping by that level's own code column.
  The finest level MUST NOT be dissolved; its output is the loaded input
  itself.
- Every column not at or above a given level's own detected depth MUST be
  dropped unconditionally (via the target schema), never triggering the
  auto-drop warning `dissolve` would otherwise log for a genuinely
  finer-level column.

## Outputs

- `package-polygons` MUST produce one output file per detected level.
- Each level's output MUST pass the hard gate in `docs/reference/shared.md`
  (no overlap; a gap at or below `SNAP_TOLERANCE` blocks export, a wider
  one does not).
- `package-polygons` MUST also export an issues report per level, using the
  shared schema in `docs/reference/shared.md`. A level's issues report MUST
  be produced only when it has at least one row.
- The finest level's own output MUST be skipped (no file written, no
  `check_overwrite` call) when its computed path resolves to the same file
  as the input; otherwise it MUST be written as a plain copy of the loaded
  input.

## Configuration (`api.package_polygons.package_polygons()` / CLI)

- `package-polygons` MUST process exactly one input file per call.
- `output_path`, if given, MUST contain a literal `{n}` placeholder,
  formatted per level; `package-polygons` MUST raise `ValueError` if it is
  given without one. If omitted, each level's output path MUST default to
  the input path with an `_admin{n}` suffix.
- `issues_path` follows the same `{n}`-template-or-omitted rule as
  `output_path`, defaulting per level to that level's own output path with
  an `_issues` suffix.
- `package-polygons` MUST raise `FileExistsError` for any level whose
  output or issues path already exists and overwriting wasn't requested.
- `step`, if given, MUST be one of `inputs`, `dissolve`, `outputs`; any
  other value MUST raise `ValueError`.
- `target_schema_path`, if omitted, MUST default to the bundled generic
  target schema.
