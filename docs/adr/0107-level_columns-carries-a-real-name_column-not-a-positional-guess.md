# 0107: `LevelColumns` carries a real `name_column`; `code-update` no longer guesses one positionally

## Status

Accepted.

## Context

`code_update/_02_levels.py`'s `_resolve_side()` picked each level's name
column as `identity_columns[1]` in effect (the first non-canonical entry
in `cols.identity_columns`), never checking that the column it picked was
actually name-shaped. For a level with no naming anchor to filter against
(a single, standalone level with no sibling level to anchor a prefix/suffix
against, `detect_level_columns()`'s "no anchor" branch), `identity_columns`
is every column structurally tied to that level, unfiltered, including any
plain numeric attribute that happens to be 1:1 with the code column
(`area_sqkm`, `center_lat`, `center_lon` in real COD-AB admin1 data).

`_looks_code_shaped()` (`core/schema_map/_02_map.py`) classifies a column
as `role="code"` whenever most of its values contain a digit, with no
exclusion for a numeric (non-code) type; a `DOUBLE` column like `area_sqkm`
or `center_lat` satisfies this trivially, so `resolve_columns()` assigns it
`role="code"` right alongside the real pcode column. This pre-existing gap
in a shared, heavily-tested primitive (used by every tool that calls
`detect_level_columns_or_single()`) is out of scope for this fix: it needs
the project's own exhaustive real-data retest discipline before touching
it, not a one-off patch alongside an unrelated bug.

Running `code-update` against a real CAF (Central African Republic) admin1
old/new portolan pair with `--link-by-name` surfaced the consequence
directly: `_resolve_side()`'s positional guess landed on `area_sqkm`
instead of `adm1_name`, so identity-linking silently compared area values
instead of names, producing a `relationship_class` distribution that
didn't match a plain `change` run against the same pair (extra `complex`
clusters, missing `modified` ones) despite both reusing the identical
classification engine.

## Decision

`LevelColumns` gains a `name_column: str | None` field, populated by
`detect_level_columns()` from the same `role` information it already
computes for `has_code` (the first column in that level's own set with
`rows[c].role == "name"`), in both the anchored and no-anchor branches.
`detect_leaf_level()` sets it to the leaf's own sole column, since a
name-only leaf's column already is its name. `_resolve_side()` now reads
`cols.name_column` directly instead of guessing from list position.

## Consequences

`code-update`'s identity-linking (`--link-by-code`/`--link-by-name`) now
defaults to the column `schema_map` actually resolved as this level's name,
not whichever non-canonical column happened to sort first. A level whose
only identity columns are code and name (every existing test fixture, and
most multi-level real data, where per-level anchoring already filters
`identity_columns` down to just those two) sees no behavior change. The
`area_sqkm`/`center_lat`/`center_lon`-style misclassification itself
(`_looks_code_shaped()` having no numeric-type exclusion) remains
unaddressed; a level whose real name column also happens to look
digit-shaped (e.g. contains a numeral, like `"Province 1"`) can still be
misclassified as `role="code"` and excluded from `name_column` entirely,
falling back to `None`.
