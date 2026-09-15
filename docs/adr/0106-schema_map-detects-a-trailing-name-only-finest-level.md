# 0106: `schema_map` detects a trailing name-only finest level; `code-refactor`/`code-update` raise on it

## Status

Accepted.

## Context

A finest-level input with a name column but no code column at that level
(e.g. `adm4_name` present, `adm4_pcode` never assigned yet) went entirely
undetected: `resolve_columns()`'s chain-building requires containment to
hold globally across the whole table, but a bare name column's own values
routinely repeat under different parents (real ZMB admin4 data has ward
names like "Luangwa" appearing under 7 different districts), so the
finest level's own edge into the chain never qualified. The column fell
through with `role=None, level=None`, invisible to every caller of
`detect_level_columns()`/`detect_level_columns_or_single()`
(`code-refactor`, `code-update`, `package-polygons`, `package-points`,
`package-lines`, `schema-fill`), not just flagged as codeless. `code-
refactor` silently produced no code at all for that level; `schema-fill`'s
own `missing code column` check never ran against it either, since it
never appeared in `detect_level_columns()`'s output to begin with.

## Decision

`core.schema_map._level_columns.detect_leaf_level()` mirrors the existing
`detect_root_level()` at the opposite end of the chain: it looks one level
past the deepest one `_build_chain()` already found, using the same
naming-anchor mechanism (`_level_anchors()`) applied per column family
(`group_families_by_level()`), so it can find a column sharing the
established `adm{n}_name` naming pattern even when no matching `adm{n}_pcode`
exists. Validity is checked scoped to the immediate parent
(`(parent_code, candidate)` pairs are each distinct, tolerating the same
sparse-noise allowance every other containment check in this module uses),
never globally: a repeated name under different parents is expected, not
disqualifying. `detect_level_columns()` calls it unconditionally and
appends the result at `max(level) + 1` with `has_code=False`, so every
existing caller now sees this level instead of never receiving it.

`code_refactor/_02_levels.py` and `code_update/_02_levels.py` both already
had a `has_code` field to check but never checked it; both now raise
`ValueError` ("no existing code column to overwrite") when a resolved
level lacks one, rather than silently skipping it (`code-refactor`, the
original bug) or silently ranking-and-overwriting the name column in place
(the naive fix, which would destroy the only human-readable data at that
level). Neither tool can create a new column that doesn't already exist in
the source (`detect_levels()`'s explicit-override path has the same
precondition), so a codeless level's only path forward is a source that
actually has one, via `--code-field`/`--code-field-a`/`--code-field-b`.

## Consequences

`package-polygons` against a similarly-shaped input now correctly dissolves
one more coarser level than before: previously it mistook the deepest
*coded* level for the finest level overall and skipped dissolving it;
now the genuinely-finest name-only level is what gets skipped, and the
real finest coded level is dissolved like any other. `schema-fill`'s own
`missing code column for level(s)` check now actually fires against this
shape, closing a validation gap that previously let it through silently.
A fully-coded input (every level already has its own code column) sees no
behavior change at all: `detect_leaf_level()` only ever finds something to
add when the chain's own deepest level isn't already the table's last one.
