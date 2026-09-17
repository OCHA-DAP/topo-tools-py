# 0104: `code-refactor` re-ranks every unit rather than reformatting its raw source value

## Status

Accepted.

## Context

A cold-start input's own raw hierarchy column (a GADM `GID_1` like
`AFG.1_1`, a plain integer with gaps, or an arbitrary string) is rarely
clean enough to zero-pad and reuse directly. It may be non-numeric,
gappy relative to its siblings, or duplicated across sibling groups in
the file. Reformatting it in place (stripping non-digits, zero-padding
what's left) would preserve a source ordering that isn't guaranteed to
be meaningful or unique, and would produce undefined output on a
genuinely non-numeric value.

## Decision

`code-refactor`'s `_03_assign` stage never reformats a raw value in
place. Every level's own distinct values are ranked under their
immediately-coarser level's already-assigned code, sorted by their own
raw pre-assignment value (`ROW_NUMBER() OVER (PARTITION BY parent ORDER
BY sort_columns)`, `core.code.assign_new_codes()`), then assigned a
fresh, sequential, zero-padded integer tail. The raw value's only role is
as a sort key, never as source material for the output code itself.

## Consequences

Two runs against the same input in the same row order always produce the
same codes (deterministic ranking), but the assigned code carries no
relationship to the raw source value's own content, only its rank among
siblings. There is no COD-AB-specific multi-column tie-break (`srcid`
then `name` then `name1`-`name3`) built into this ranking; the sort key
is a single column, either structurally detected or given via
`--code-field`. A future COD-AB profile (`docs/adr/0101`) is the intended
place for a richer, convention-specific tie-break, layered on top of this
same single-column mechanism rather than replacing it.
