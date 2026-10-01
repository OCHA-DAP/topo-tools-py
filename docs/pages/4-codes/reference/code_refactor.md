---
status: draft
title: "code-refactor"
---

## Inputs

- `code-refactor` MUST read the one input and reproject it to EPSG:4326 via
  `core.io.read_and_reproject()`. It takes exactly one flat input at the
  finest level, hierarchy embedded as columns (the same shape
  `schema-fill`/`package-polygons` expect).

## Level resolution

- `code-refactor` MUST resolve each level's own code column either via an
  explicit `name_field`/`code_field` pair (each an `{n}`-template, given
  together or not at all, raising `ValueError` if only one is given, the
  same contract `schema-map`/`package-polygons` use), or, when both are
  omitted, via structural auto-detection
  (`core.schema_map.detect_level_columns_or_single()`, cardinality/
  containment only, no naming convention assumed).
- `code-refactor` MUST raise `ValueError` ("no admin hierarchy level
  detected") if structural auto-detection finds zero levels.
- In structural mode, `code-refactor` MUST raise `ValueError` ("no existing
  code column to overwrite") if any resolved level has no code column at all
  (e.g. a trailing finest level with only a name column, see
  `docs/adr/0106`), rather than silently skipping that level or overwriting
  its name column.
- With an explicit `name_field`/`code_field` pair, a level with a name
  column but no code column MUST get a code column seeded from its names; a
  level with neither MUST raise `ValueError`.
- `code-refactor` MUST raise `ValueError` in structural mode ("group units like a
  level") if detection sets any column aside as a supplemental coarser
  grouping, and ("a coarser level merged into this one") if any member of
  a level's group-by has over 30% fewer values than its code under each
  parent, rather than coding a merged or skipped level (see
  `docs/adr/0121`).
- Every resolved level MUST be renumbered to a clean, relative `1..N`
  sequence, coarsest first; a genuinely constant coarsest column (e.g. a
  single-country file's own admin0 code) is dropped before reaching this
  step and never becomes a level.
- A source column that never resolves into a level (including a constant
  admin0-shaped one) MUST be left completely untouched: `code-refactor`
  never stamps `root_code` into its own output column, it's used only as
  the literal parent for level 1's own assignment.

## Assignment

- `source_codes` MUST be one of `replace` (default), `embed`, `copy`.
- Under `replace` and `copy`, for each resolved level `1..N`, ascending,
  `code-refactor` MUST rank that level's own distinct code-column values
  under their immediately-coarser level's already-assigned code (or
  `root_code`, for level 1), sorted by their own raw, pre-assignment value,
  and overwrite the column in place with a freshly assigned, sequential,
  zero-padded code (`core.code.assign_new_codes()`).
- Under `replace` and `copy`, a level's raw source value MUST NOT be reused
  as-is (zero-padded or passed through unchanged): it may be non-numeric,
  gappy, or duplicated across siblings, so every value is always re-ranked
  into a fresh sequential integer before formatting.
- Under `copy`, each level's source code column MUST be copied to its next
  free numbered sibling (`adm1_code` to `adm1_code1`), placed right after
  it, before assignment; a seeded level gets none.
- Under `embed`, a level with a source code column MUST be coded as its
  parent's code (or `root_code`), then `delimiter`, then its own source
  value unchanged, and a seeded level is ranked as under `replace`. `embed`
  MUST raise `ValueError` if a row of a source-coded level has no source
  code, or if `delimiter` is empty and that level's source codes differ in
  length (see `docs/adr/0122`).
- The sort key MUST be the resolved code column's own raw value; there is
  no COD-AB-specific multi-column tie-break (e.g. `srcid` then `name` then
  `name1`-`name3`).
- Each level's codes MUST be zero-padded to that level's own width:
  `min_width` itself, its entry in a per-level list, or under `auto` the
  widest tail the level needs (see `docs/adr/0123`).
- A parent whose child count exceeds `10 ** width - 1` (999 at width 3)
  MUST NOT have its already-assigned, lower-numbered children's codes
  repadded; the overflowing child's own tail simply grows past the width
  instead.

## Outputs

- `code-refactor` MUST export the finest-level table, every resolved
  level's code column overwritten in place, as the main output, same
  format as the input. It performs no topology hard gate: geometry is
  never modified, only attribute columns are rewritten.
- `code-refactor` MAY write an issues report when `issues_path` is given
  and a numbered level (any level with a fixed width, except a
  source-coded one under `embed`) has a parent over overflow capacity; it MUST delete any
  stale file already at that path when the run produces zero overflow
  rows. Schema: `kind` (`'digit-overflow'`), `level`, `parent_code`,
  `assigned_code` (the overflowing parent's highest code), `child_count`,
  `min_width` (that level's width), `reason`.

## Configuration (`api.code_refactor.code_refactor()` / CLI)

- `code-refactor` MUST process exactly one input file per call.
- `root_code`, `delimiter`, and `min_width` MUST all be given explicitly
  (no default), validated via `core.code.resolve_code_format()`:
  `root_code` non-empty, `delimiter` exactly one character, or empty under
  `source_codes='embed'`, `min_width` one positive width, a comma list of
  positive widths with exactly one per numbered level (coarsest first),
  or `auto`. `root_code` is opaque, never shape-checked (a disputed-
  territory or otherwise non-ISO3 string works identically to an ISO3
  one).
- `output_path`, if omitted, MUST default to `input_path` with a `_coded`
  stem suffix.
- `issues_path`, if omitted, MUST default to `output_path` with an
  `_issues` stem suffix and a `.csv` extension. It MUST be one of
  `core.code.TABLE_COPY_OPTS`'s extensions (a tabular format; the issues
  report has no geometry column), raising `ValueError` otherwise.
- `code-refactor` MUST raise `FileExistsError` for `output_path` or
  `issues_path` if either already exists and overwriting wasn't requested.
- `step`, if given, MUST be one of `inputs`, `levels`, `assign`, `outputs`;
  any other value MUST raise `ValueError`.

## Examples

### Example 1: structural auto-detection, no code column exists yet

    topo-tools code-refactor admin2.geojson --root-code AFG --delimiter . --min-width 3

### Example 2: explicit level columns, ambiguous auto-detection

    topo-tools code-refactor admin2.geojson --root-code AFG --delimiter . --min-width 3 \
      --code-field adm{n}_code --name-field adm{n}_name

### Example 3: overflow issues report

Writes `admin2_coded.geojson` and, only if any parent exceeds `10 **
min_width - 1` children, `admin2_coded_issues.csv`:

    topo-tools code-refactor admin2.geojson admin2_coded.geojson --root-code AFG --delimiter . --min-width 3

### Example 4: source codes embedded without a delimiter

    topo-tools code-refactor admin3.geojson --root-code XY --delimiter '' --min-width auto \
      --source-codes embed --code-field adm{n}_code --name-field adm{n}_name

### Example 5: source codes kept in sibling columns

    topo-tools code-refactor admin3.geojson --root-code XYZ --delimiter . --min-width 3 \
      --source-codes copy --code-field adm{n}_code --name-field adm{n}_name

### Example 6: one width per level

    topo-tools code-refactor admin3.geojson --root-code XYZ --delimiter . --min-width 2,3,4
