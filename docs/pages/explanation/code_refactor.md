---
title: "code-refactor"
---

`code-refactor` cold-starts a hierarchical code on any flat, finest-level
input: no existing code column is assumed, only a hierarchy embedded as
columns (the same shape `package-polygons`/`schema-fill` expect). Four
stages, each a numbered module in `topo_tools/core/code_refactor/`.

## `_01_inputs`: load

Loads and reprojects the one input via `core.io.read_and_reproject()`.
`code-refactor` never coverage-cleans: it rewrites attribute columns only,
geometry is untouched throughout the whole pipeline.

## `_02_levels`: resolve, don't assume

Level resolution reuses `package-polygons`'s own two-path contract rather
than inventing a third: `resolve_explicit_target_schema(name_field,
code_field)` first, and if that returns `None` (neither flag given),
structural auto-detection (`detect_level_columns_or_single()` +
`verify_functional_cluster()`) takes over. Zero levels detected raises
`ValueError`, since a hierarchy that can't be located at all has nothing
for the tool to rank. A resolved level with no code column at all (only a
name, `has_code=False`, see `docs/adr/0106`) also raises `ValueError`: `code-
refactor` only ever overwrites an existing column's values, it never
creates one, so a codeless level needs `--code-field` pointed at a real
column before it can be ranked at all.

Resolved levels are renumbered to a clean `1..N`, coarsest first,
regardless of how many raw columns existed or what they were named. A
genuinely constant coarsest column (a single-country file's own admin0
code, for instance) never becomes a level; it's dropped before
renumbering. This is why `root_code` is never stamped as its own output
column: level 1 already has a real parent, the `root_code` string itself,
so there's no level 0 for `root_code` to occupy. `_03_assign.py`'s `if 0
in levels:` branch exists for a `levels` dict that could in principle
carry a `0` key, but `_02_levels.main()` never actually produces one, so
that branch never executes against real input.

## `_03_assign`: chained, not independent, per level

Each level `1..N`, ascending, is assigned via one `core.code.
assign_new_codes()` call: rank that level's own raw values under their
immediately-coarser level's already-assigned code (or the literal
`root_code`, for level 1), and overwrite the column in place with a fresh
sequential, zero-padded code.

This deliberately chains level to level, unlike `package-polygons`'s
independent per-level dissolves (each of which stands alone against the
original finest table). Ranking a level's units requires that level's own
parent code to already exist, so level 2 can't be assigned until level
1's own assignment has produced real parent codes to group under; there's
no way to parallelize or reorder the levels the way `package-polygons`'s
independent dissolves can.

Every source value is re-ranked into a fresh integer before formatting,
never passed through as-is (see `docs/adr/0104`): a raw hierarchy column
(a GADM `GID_1` like `AFG.1_1`, or a plain integer with gaps) is rarely
clean enough to zero-pad directly, and even when it happens to look
clean, nothing guarantees it's unique or gap-free across every sibling
group in the file.

## `_04_outputs`: export plus overflow reporting

The finest-level table, every resolved level's code column now
overwritten in place, is exported as the main output via
`export_geometry_table()`, same format as the input.

`_write_overflow_issues()` groups distinct assigned codes per level by
their own parent prefix, flags any group whose count exceeds `10 **
min_width - 1`, and reports the parent's own highest-tail-integer
assigned code alongside the count. A run with zero overflow rows deletes
any stale issues file already sitting at `issues_path`
(`.unlink(missing_ok=True)`), so a re-run after fixing an overflowing
input doesn't leave a misleading old report behind.

## Table naming

Stages share one DuckDB connection under `f"{input_basename}_code_refactor"`
as their own `name`, distinct from any `code-update` run against a
related file (which uses its own `name`, scoped per NEW input), so the two
tools never collide on the same `tmp_dir`.
