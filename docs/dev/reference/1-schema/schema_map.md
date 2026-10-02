---
title: "schema-map"
sidebar:
  order: 4
  badge:
    text: Draft
    variant: caution
---

## Modes

- By default, `schema-map` MUST map a crosswalk from the input's
  structure, write it as CSV, and apply it, writing the mapped layer.
- With `csv_input` (`--csv`), it MUST skip mapping and apply
  that crosswalk CSV, writing only the mapped layer.
- With `map_only` (`--map-only`), it MUST map and write only the
  crosswalk CSV.
- `schema-map` MUST raise `ValueError` if `csv_input` is given with
  `map_only`, `csv_output`, or `level`, or if `map_only` is given
  with an output path.

## Inputs

- `schema-map` MUST read the input and reproject it to EPSG:4326 the same way
  every other tool does, via `core.io.read_and_reproject()`.
- `schema-map` MUST take `name_field`/`code_field` strings, each containing a
  `{n}` placeholder (e.g. `adm{n}_name`/`adm{n}_code`); these supply output
  naming only, never matching vocabulary. Both MUST be given together, or
  both omitted; if both are omitted, it MUST default to `adm{n}_name`/
  `adm{n}_code`.
- `schema-map` MUST raise `ValueError` if only one of `name_field`/
  `code_field` is given, or if either lacks a `{n}` placeholder.
- `schema-map` MUST exclude any column matching `core.constants.is_noise_column()`
  from candidate columns entirely; they never appear in the crosswalk, not
  even as `unmatched`. A column matches if its name, case-insensitively,
  either exactly equals an entry in `core.constants.NOISE_COLUMNS`
  (`objectid`, `globalid`, `cat`, `shape_leng`/`shape_length`/`shape__length`,
  `shape_area`/`shape__area`, `ogc_fid`/`ogc_fid_orig`/`fid_orig`), or
  equals one after stripping a trailing GDAL collision suffix
  (`_\d+`, e.g. `fid_1` -> `fid`), or is exactly 10 characters long (the
  ESRI Shapefile DBF driver's field-name limit) with that stripped base a
  prefix of a `NOISE_COLUMNS` entry (e.g. `Shape_Le_1` -> `shape_le`, a
  prefix of `shape_length`, the DBF-truncated form of a duplicate field).
- A `csv_input` MUST be a CSV with a `source_column` column (as
  written by `schema-map`, or a hand-edited copy), one row per source
  column, with or without a leading UTF-8 byte-order mark, else
  `ValueError`. A row with a blank `source_column` MUST be
  skipped.
- `schema-map` MUST raise `ValueError` if the crosswalk's `source_column`
  set does not exactly equal the input's own column set, excluding any
  column matching `core.constants.is_noise_column()`, if it lists the same
  `source_column` twice, if two rows share a non-null `target_column`, or
  if a `target_column` is reserved (`fid`, `geom`, `geometry`).

## Matching

`schema-map` MUST NOT use any column name, alias, or vocabulary as a matching
signal, and MUST NOT use a value-shape assumption to decide chain
membership either; every candidate column's own values are relationally
tested against every other candidate column's values, never its name.
Value shape (`_looks_code_shaped()`, majority of non-null values
containing a digit) MUST only be consulted as a fallback for the `code`
vs. `name` role of a chain column once its level is already resolved.
When a level has no name and two or more code-shaped columns that don't
embed the parent, the target schema's `name_field`/`code_field` text in a
column's name MAY break the tie, as long as one code remains (see
`docs/adr/0121`). See
`docs/dev/explanation/1-schema/schema_map.md` and `docs/adr/0064`, `docs/adr/0066` for the
empirical justification.

- An all-null candidate column (`COUNT(DISTINCT) = 0`) MUST NOT be
  eligible for chain group formation: two all-null columns are trivially,
  vacuously bijective with each other and with nothing else, no real
  evidence either way, the same principle already applied to `_embeds()`
  (see `docs/adr/0069`). It still MUST appear in the crosswalk as
  `unmatched`. A float or decimal column holding any non-whole value MUST
  be excluded the same way, from both chain groups and bracketing.
- Every remaining candidate column, code or name alike, MUST be grouped by
  identical `COUNT(DISTINCT)` (constants are kept, not dropped: a
  single-country file's admin0 code is legitimately constant), and
  same-count fully-populated columns clustered by pairwise verified
  bijection (two columns merge only if bijective with each other; a third
  column sharing their count but not their bijection MUST NOT prevent the
  other two from merging).
- A column with any NULL MUST cluster only by 1:1 correspondence on the
  rows where both columns are populated, over at least 10 joint values,
  or over every value of both columns (and at least 2). Column names MUST
  NOT be consulted. Sparse columns populated on identical rows MUST group
  first. A group or lone column that matches more than one cluster MUST
  join none.
- The admin hierarchy MUST be built as the longest path through every
  coarser/finer pair of level-groups that satisfies containment
  (`GROUP BY finer HAVING COUNT(DISTINCT coarser) > 1` MUST return zero
  rows, or exactly one violating group, for every coarser/finer column
  pair between the two groups; see the single-violator tolerance below),
  not just cardinality-adjacent pairs; this lets a finer level reconnect
  past a level that doesn't nest cleanly (a "loose" cross-cutting
  attribute that happens to be embedded inside a compound code, e.g. an
  urban/rural classifier) instead of severing the rest of the chain. A
  candidate edge MUST additionally require either the coarser group's
  `COUNT(DISTINCT)` to be exactly 1 (a true constant, exempt from
  embedding), or some column in the finer group to textually contain
  (`contains(child, parent)`, row for row over non-null pairs, tolerating
  a single violating value) some column in the coarser group, or, if no
  coarser/finer group pair anywhere in the file has embedding evidence at
  all, containment alone (see `docs/adr/0070`). When multiple candidates
  tie for the longest path, the one with more same-level companion
  columns MUST win, then the one with the higher (finer) `COUNT(DISTINCT)`.
- Both the containment and embedding checks above MUST tolerate exactly
  one violating value the same way a NULL already carries no evidence: a
  missing-value sentinel (e.g. `"No_Pcode"`) reused across many real
  parents, never a hardcoded literal, only "exactly one distinct value
  explains every violation". More than one distinct violator MUST fail
  strictly, a genuine multi-value anomaly, not a placeholder (see
  `docs/adr/0071`).
- With `level` given, the finest resolved level MUST be numbered `level`
  and each coarser one by nesting depth from it, and `schema-map` MUST raise
  `ValueError` if that would number any resolved level below 0. Without
  `level`, a constant coarsest level MUST be numbered 0 and any other
  coarsest level 1, with a logged warning.
- Within a resolved chain level, each column's role MUST be `code` if
  either it textually contains (`contains(child, parent)`) some column at
  the level's resolved parent, or it independently passes
  `_looks_code_shaped()`; otherwise it MUST be `name`. This check MUST run
  per column, never deferred to a sibling's embedding result: a column
  that fails to embed its parent MUST still resolve to `code` on its own
  value shape rather than defaulting to `name` just because another
  sibling in the group embedded the parent (see `docs/adr/0067`). Same-
  role companions at one level MUST each get a numbered `target_column`
  from `code_field`/`name_field` (a code that embeds its parent first,
  then source-column order; the first gets the bare rendered template,
  each next one a numbered sibling of it, see `docs/adr/0118`).
- Every non-code-eligible column MUST be bracketed into the chain by its
  own `COUNT(DISTINCT)`: it lands at level `k` if `code_count[k-1] <
  distinct_count <= code_count[k]` (`code_count[-1]` is 0); a column
  whose count doesn't fall into exactly one bracket MUST be left
  unmatched.
- A bracketed column MUST additionally pass a same-level function check
  against that level's code column (`GROUP BY code HAVING COUNT(DISTINCT
  candidate) > 1` MUST return zero rows) before it's eligible for
  confidence `name` or `supplemental`; a column that fails this check
  entirely (neither a subset nor superset of the level) MUST be
  confidence `ambiguous`, `target_column` empty.
- A function-passing column MUST be confidence `supplemental`,
  `target_column` empty, when its level's chain group already has a
  resolved `name` role member AND its own collapse ratio (`1 -
  COUNT(DISTINCT candidate) / level_unit_count`) exceeds `0.30`; a
  bijective (exact) same-level companion cannot reach the bracket step at
  all, since bijection would already have merged it into the chain group
  at the grouping step, so a function-passing bracket candidate is always
  a genuine, coarser superset of the level (by pigeonhole, an onto
  function between equal-cardinality sets is also one-to-one, so a
  non-bijective function-passing candidate must be coarser) unless its
  collapse is within that tolerance, in which case it's treated as a
  same-level translation/transcription variant instead (see
  `docs/adr/0076`). When the level's chain group has no `name` role
  member yet, or the candidate's collapse ratio is `<= 0.30`,
  function-passing candidates MUST instead resolve to confidence `name`,
  numbered `target_column` from `name_field` (same numbering scheme as
  code companions above).
- A column landing in no bracket at all MUST be confidence `unmatched`,
  `target_column` and `note` both empty.
- A resolved level MUST be excluded from output (fall through to
  confidence `unmatched`) only when its own `COUNT(DISTINCT)` is exactly
  1, a true constant; a non-constant level MUST be resolved regardless of
  its rank in the discovered chain, even at position 0. `schema-map` has no way
  to tell a genuine admin0 constant from a coarsest-in-file level that
  merely isn't actually admin0 (a file with no country column at all)
  without `level`; it only excludes columns with no real variation to report.
- `target_column` MUST be non-empty only for a `code`/`name` row; every
  `ambiguous`/`unmatched` row's `target_column` MUST be empty, since
  applying drops any source column whose crosswalk `target_column` is
  empty (see "Applying") and a human, not `schema-map`,
  decides whether to keep such a column and under what name.
- `schema-map` MUST NOT call an LLM or any external service; matching is
  embedding and cardinality/containment logic only.

## Applying

- A source column whose `target_column` is null or empty MUST be dropped.
  Every other source column MUST be renamed to its `target_column`. The
  geometry column MUST pass through unchanged.
- A freshly mapped crosswalk MUST order columns by the
  `name_field`/`code_field` templates: levels deepest first, and within
  each level its name-template columns, then any other column with that
  level's prefix and number, then its code-template columns, numbered
  siblings in numeric order. Every other column follows in input order.
  A `csv_input` MUST set column order by its row order, after `geometry`,
  with a warning (no reordering) when a column's numbered siblings
  (`adm2_name1`, `adm2_name2`) don't follow it in numeric order.
- Rows MUST be sorted by the deepest level's own code column, by value
  (text codes as text), NULLs last, ties in input order. With no
  code-template column, rows MUST keep their input order, with a warning.

## Outputs

- `schema-map` performs no topology hard gate at all; it only inspects and
  never mutates geometry.
- Unless given a `csv_input`, `schema-map` MUST produce a crosswalk file,
  UTF-8 with a byte-order mark, one CSV row per source column with exactly
  four columns: `source_column`, `target_column`,
  `unique_count`, `note`. Every row MUST carry a `unique_count`: for a
  row bracketed to a level (`code`, `name`, `ambiguous`, or
  `supplemental`), `COUNT(DISTINCT parent_code, this_column)` against
  the level above it, catching a value reused across parents (e.g.
  "County 1" under two different provinces) that a same-column distinct
  count alone would hide; for any other row (an excluded constant level,
  or fully `unmatched`), the column's own `COUNT(DISTINCT)`. A
  `code`/`name` row's `note` MUST be empty, since `target_column` already
  encodes the level and `unique_count` already encodes the cardinality
  signal. A bracketed `ambiguous` row's `note` MUST be exactly
  `"ambiguous, level {k}"`; a bracketed `supplemental` row's `note` MUST
  be exactly `"supplemental, superset of level {k}"`. An `unmatched`
  row's `note` MUST be empty.
- Rows MUST be ordered by resolved level descending (finest first,
  matching COD-AB's own-level-then-ancestors order), name before code
  within a level, then every `unmatched` column last in the source
  file's own column order.
- `schema-map` MUST NOT modify the input file.

## Configuration (`api.schema_map.map()` / CLI)

- `schema-map` MUST process exactly one input file per call.
- The mapped-layer path MUST default to the input path with a `_mapped`
  suffix, and MUST raise `ValueError` if it ends in `.csv`, pointing to
  `csv_output`.
- The crosswalk path (`csv_output`, `--csv-output`) MUST
  default to the input path with a `_crosswalk` stem suffix and a `.csv`
  extension.
- `schema-map` MUST raise `FileExistsError` if an output it writes already
  exists and overwriting wasn't requested.
- `level`, if given, MUST be a non-negative integer (`--level`).
- `step`, if given, MUST be one of `inputs`, `map`, `apply`, `outputs`,
  minus the stage the mode skips (`map` with `csv_input`, `apply`
  with `map_only`); any other value MUST raise `ValueError`.

## Examples

### Example 1: basic run, default (`adm{n}_name`/`adm{n}_code`) naming, output names chosen automatically

    topo-tools schema-map example.geojson

### Example 2: custom target naming

    topo-tools schema-map example.geojson --name-field state_name --code-field state_code

### Example 3: explicit outputs

    topo-tools schema-map example.gpkg example_mapped.gpkg --csv-output example_crosswalk.csv

### Example 4: apply an edited crosswalk

    topo-tools schema-map example.geojson --csv example_crosswalk.csv

### Example 5: only write the crosswalk

    topo-tools schema-map example.geojson --map-only

### Example 6: number levels from the file's own admin level

    topo-tools schema-map admin3.geojson --level 3

### Example 7: number a multi-country file

    topo-tools schema-map global_admin1.geojson --level 1
