---
status: draft
title: "schema-crosswalk"
---

See `docs/reference/README.md` for the MUST/SHOULD/MAY convention, and
`docs/reference/shared.md` for rules `schema-crosswalk` shares with other tools.

## Matching and renaming

- `schema-crosswalk` MUST map a source-column -> target-schema crosswalk exactly
  as standalone `schema-map` does (see `docs/reference/schema_map.md`): the same
  matching passes, noise-column exclusion, and output ordering rules
  apply unchanged, `schema-crosswalk` calls `schema-map`'s own matching stage directly
  rather than owning separate logic.
- `schema-crosswalk` MUST then apply that freshly-generated crosswalk exactly as
  standalone `schema-refactor` does (see `docs/reference/schema_refactor.md`): the same
  coverage-validation, renaming, dropping, and ordering rules apply
  unchanged, using its own `name_field`/`code_field`,
  `schema-crosswalk` calls `schema-refactor`'s own validation and rename stages directly.

## Outputs

- `schema-crosswalk` MUST always produce both the crosswalk CSV (same shape as
  standalone `schema-map`'s output) and the mapped output file (same shape as
  standalone `schema-refactor`'s output).
- `schema-crosswalk` performs no topology hard gate at all; neither underlying
  stage touches geometry.

## Configuration (`api.schema_crosswalk.crosswalk()` / CLI)

- `schema-crosswalk` MUST process exactly one input file per call.
- The mapped-output path MUST default to the input path with a `_mapped`
  suffix. The crosswalk path MUST default to the input path with a
  `_crosswalk` stem suffix and a `.csv` extension.
- `schema-crosswalk` MUST raise `FileExistsError` if either output path already
  exists and overwriting wasn't requested.
- `level` MUST behave as in `schema-map`.
- `step`, if given, MUST be one of `inputs`, `schema-map`, `apply`, `outputs`;
  any other value MUST raise `ValueError`.
- To iterate on a `schema-crosswalk`-generated crosswalk (hand-edit it, then
  re-apply), re-run standalone `schema-refactor` on the written crosswalk file;
  re-running `schema-crosswalk` always maps fresh, discarding any hand edits.

## Examples

### Example 1: basic run, default (`adm{n}_name`/`adm{n}_code`) naming, output names chosen automatically

    topo-tools schema-crosswalk example.geojson

### Example 2: custom target naming

    topo-tools schema-crosswalk example.geojson --name-field state_name --code-field state_code

### Example 3: explicit outputs

    topo-tools schema-crosswalk example.gpkg example_mapped.gpkg example_crosswalk.csv --name-field state_name --code-field state_code

### Example 4: iterate on a hand-edited crosswalk

    topo-tools schema-crosswalk example.geojson
    # review/edit example_crosswalk.csv, then re-apply without re-mapping:
    topo-tools schema-refactor example.geojson example_crosswalk.csv --overwrite

See [`schema-map`](schema_map.md) and [`schema-refactor`](schema_refactor.md) for the two
underlying tools this composes.
