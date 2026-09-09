# package

See `docs/reference/README.md` for the MUST/SHOULD/MAY convention.

## Behavior

- `package` MUST call `package-polygons`, `package-points`, and
  `package-lines` against the same input path and the same `name_field`/
  `code_field` (or the same auto-detection, when both are omitted), each
  reading and reprojecting the input independently (no shared connection
  or table across the three).
- `package` MUST NOT expose `--step` or a separate issues-path option; each
  sub-tool manages its own connection and derives its own issues path from
  its own output path.

## Output path templating

- `output_path`, if given, MUST contain a literal `{x}` placeholder;
  `package` MUST raise `ValueError` if it is given without one.
- `{x}` MUST be substituted per sub-call with a fixed word: `admin{n}` for
  `package-polygons` (itself still `{n}`-templated per level), `points`
  for `package-points`, `lines` for `package-lines`. No other placeholder
  is exposed.
- If `output_path` is omitted, every sub-tool MUST receive `output_path=None`
  and fall back to its own default naming.

## Configuration (`api.package.package()` / CLI)

- `package` MUST process exactly one input file per call.
- `overwrite`, `threads`, `tmp_dir`, `debug`, `name_field`, and `code_field`
  MUST be passed through unchanged to all three sub-calls.
- `package` MUST NOT expose `depth_column`: `package-points` and
  `package-lines` each run with their own default (`adm_lvl`). An input
  that already has its own `adm_lvl` column (raising `ValueError` in
  either sub-tool) MUST be run through `package-points`/`package-lines`
  directly with a non-colliding `--depth-column` instead of through
  `package`.
