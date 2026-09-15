# Code Explanation

`core.code` is the shared primitive behind `code-refactor` and
`code-update` (`docs/explanation/code_refactor.md`,
`docs/explanation/code_update.md`): a neutral leaf, like `core.assign` or
`core.dissolve`, with no `api.*()`/CLI of its own. It carries every piece
of format/cascade/rewrite logic a hierarchical code needs, generic to any
organization's own convention, not hardcoded to COD-AB's (see
`docs/adr/0101`).

## `CodeFormat`

```python
@dataclass(frozen=True)
class CodeFormat:
    root_code: str
    delimiter: str
    min_width: int
```

No field has a default value. `resolve_code_format(root_code, delimiter,
min_width)` is a thin validating constructor, not a defaults-filling one:
non-empty root, single-character delimiter, positive `min_width`.
`root_code` is opaque everywhere, never shape-checked, so a disputed-
territory prefix (`XKO`, or any user-assigned string) works identically to
an ISO3 one.

## Cascade: ranking, not reformatting

`assign_new_codes(conn, table, *, id_column, parent_column, sort_columns,
code_column, fmt, existing_codes=None)` is the one function both tools use
to actually mint new codes. It never reformats a raw source value in
place: rows are ranked per `parent_column` group by `sort_columns`
(`ROW_NUMBER() OVER (PARTITION BY parent_column ORDER BY sort_columns)`),
starting from `next_available_integer(existing_codes, parent_code, fmt)`
for that parent, then formatted as
`parent_code || delimiter || lpad(tail, width, '0')`. A raw source value
is never trustworthy enough to zero-pad and reuse: it may be non-numeric,
gappy, or duplicated across siblings (a real GADM `GID_1` looks like
`AFG.1_1`, not a clean rankable integer).

`next_available_integer(existing_codes, parent_code, fmt)` scans
`existing_codes` for anything starting with `f"{parent_code}{delimiter}"`,
skips a tail that still contains the delimiter (a nested, deeper code
under the same textual prefix) or isn't numeric, and returns
`max(found) + 1`, or `1` if nothing matches. It only ever looks at the
`existing_codes` list it's given, never a persisted registry; see
`docs/adr/0102` for the accepted correctness trade-off this implies for
`code-update`.

## Overflow: width grows, it never repads

`lpad` truncates an over-width string (unlike Python's `zfill`, which
never shortens), so `assign_new_codes()` widens its own target width to
`GREATEST(min_width, LENGTH(tail))` before padding. A parent's 1000th
child (at the default `min_width=3`, capacity `10**3 - 1 = 999`) gets a
4-digit tail; every child ranked below it keeps its own already-assigned
3-digit code untouched, no whole-parent repad. `code-refactor` and
`code-update` each independently detect and report this condition in
their own outputs stage (own issues report / changelog `overflow`
outcome, see their own explanation docs), `core.code` itself has no
reporting concept, only the underlying width behavior.

## Format detection

`detect_code_format(conn, table, code_column)` (used only by
`code-update`, against OLD's own already-coded finest-level column) infers
a `CodeFormat` straight from a sample of existing values (up to 10,000
distinct, non-null), rather than requiring a caller to state it:

- **`delimiter`**: the single non-alphanumeric character common to every
  sampled code. Zero or more than one candidate raises `ValueError`.
- **`root_code`**: the shared first delimiter-split component. Not
  constant across the sample raises `ValueError`, since that means
  `code_column` isn't actually this dataset's own root-anchored hierarchy
  column.
- **`min_width`**: the **mode** (most common), not the min or max, of
  every non-root component's width, pooled across every level present in
  the column (one number for the whole format, not one per level). This
  specifically avoids an overflow-widened tail at one parent (see above)
  skewing the detected width for every other, non-overflowed parent.

Any field that can't be confidently inferred raises `ValueError` rather
than falling back to a hardcoded literal; `code-update` always accepts
explicit `--root-code`/`--delimiter`/`--min-width` overrides.

## Rewrite: cascading a parent's new prefix

`rewrite_child_code(old_code, new_parent_code, fmt)` reattaches
`old_code`'s own final (tail) component onto `new_parent_code`, leaving
the tail integer and its sibling ranking completely untouched. This is
the one function that lets `code-update` cascade a coarser unit's new code
down through every unchanged/renamed descendant without re-ranking them
(`docs/adr/0103`): only the unit whose own identity actually changed gets
a fresh cascade through `assign_new_codes()`; everything nested under it
that didn't change keeps its own relative position, just under a new
prefix.

## Pure string operations

`parse_code(code, fmt)`/`build_code(components, fmt)` split/join on
`fmt.delimiter`. `parent_prefix(code, fmt)` drops a code's own last
component (raises `ValueError`, "no parent", for a root-only, single-
component code). `last_component(code, fmt)` returns a code's own final,
unpadded component. None of these validate a code's shape beyond simple
splitting; a malformed code just produces a malformed result rather than
raising, except at the two explicit validation points above.
