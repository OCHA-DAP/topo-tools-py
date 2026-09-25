---
status: draft
title: "schema-join"
---

See `docs/reference/README.md` for the MUST/SHOULD/MAY convention, and
`docs/reference/shared.md` for rules `schema-join` shares with other tools.

## Inputs

- `schema-join` MUST read one child file and one parent file, reprojecting
  both to EPSG:4326 the same way every other tool does, via
  `core.assign.load_children()`/`load_parent()`.
- `schema-join` MAY take the same `name_field`/`code_field` pair
  `schema-map` takes (each containing a `{n}` placeholder); both MUST be
  given together, or both omitted. When given, the parent's hierarchy
  columns MUST be every column in a `{n}`-numbered family under
  `name_field`'s or `code_field`'s prefix, for every level `detect_levels()` finds on the
  parent, raising `ValueError` under the same missing-level rules as
  `schema-fill`.
- When `name_field`/`code_field` are omitted, `schema-join` MUST instead
  structurally auto-detect the parent's hierarchy columns (every level's
  identity columns from `core.schema_map`'s cardinality/containment
  matcher, no naming convention assumed), raising `ValueError` if no level
  is detected.
- Only the parent's hierarchy columns are ever copied; any other parent
  column MUST be ignored.

## Assignment

- `schema-join` MUST assign each child to the single parent it shares the
  most area with (`core.assign.assign_many()`, per-child plurality, ties
  broken by lowest parent fid), measured in `EQUAL_AREA_CRS`.
- A child overlapping no parent MUST stay in the output, with every copied
  parent column NULL.

## Joining

For each parent hierarchy column:

- absent from the child: `schema-join` MUST add it, filled from the
  child's assigned parent;
- present on the child and equal (`IS NOT DISTINCT FROM`) on every
  assigned child: `schema-join` MUST skip it, leaving the child's column
  as-is;
- present on the child and different on any assigned child:
  `schema-join` MUST leave the child's column untouched and add the
  parent's values under the next free numbered sibling name (`adm2_name1`,
  then `adm2_name2` if `adm2_name1` is taken on either layer; see
  `docs/reference/shared.md`), logging a
  warning with the differing row count.

`schema-join` MUST NOT raise on a conflicting value, and MUST NOT
overwrite any child value (see `docs/adr/0109`).

## Outputs

- `schema-join` MUST NOT modify geometry, and so performs no topology
  hard gate at all.
- The output MUST keep every child row, in the shared column and row order
  (see `docs/reference/shared.md`), using `name_field`/`code_field`, or
  `adm{n}_name`/`adm{n}_code` when omitted.
- `schema-join` MUST write an issues file in the shared issues-table
  column schema, with one row per:
  - `no-parent`: a child overlapping no parent;
  - `low-overlap`: a child whose assigned parent covers less than
    `min_overlap` of its own area, with `area_m2` set to the child's area
    outside that parent and `reason` stating the covered share;
  - `value-mismatch`: a child and column where the child's value and its
    parent's value are both non-NULL and differ, with `reason` naming the
    column and both values.
- `unit_a` MUST hold the child's 1-based row number in the output file, not
  its input fid, since rows are re-sorted by code.
- `schema-join` MUST NOT write an empty issues file, and MUST remove a
  stale one at the issues path instead.

## Configuration (`api.schema_join.join()` / CLI)

- `schema-join` MUST process exactly one child file and one parent file per
  call; either MAY be an `http://`/`https://` URL to a `.parquet` file.
- The output path MUST default to the child path with a `_join` stem
  suffix, and the issues path to the output path with an `_issues` stem
  suffix (`issues_path`/`--issues-output` to override).
- `schema-join` MUST raise `FileExistsError` if either the output or the
  issues path already exists and overwriting wasn't requested.
- `min_overlap`/`--min-overlap` MUST default to `0.5` and MUST raise
  `ValueError` outside `(0, 1]`.
- `step`, if given, MUST be one of `inputs`, `assign`, `join`, `outputs`;
  any other value MUST raise `ValueError`.

## Examples

### Example 1: basic run, structural auto-detection, output name chosen automatically

    topo-tools schema-join admin3.parquet admin2.parquet

### Example 2: chain levels coarsest-first

    topo-tools schema-join admin2.parquet admin1.parquet admin2_join.parquet
    topo-tools schema-join admin3.parquet admin2_join.parquet admin3_join.parquet

### Example 3: custom target naming

    topo-tools schema-join admin3.parquet admin2.parquet --name-field adm{n}_name --code-field adm{n}_pcode

### Example 4: explicit issues path and a stricter overlap threshold

    topo-tools schema-join admin3.gpkg admin2.gpkg admin3_join.gpkg --issues-output review.gpkg --min-overlap 0.9
