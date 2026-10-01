# 0122: code-refactor embeds or copies source codes

## Status

Accepted. Supersedes `docs/adr/0104` for `source_codes='embed'`.

## Context

COD-AB p-codes released in 2026 are the country's ISO2 code followed by
each level's government code, concatenated (BHR: `BH51`, `BH51` plus a
number for admin2, which has no government code, then the block number:
`BH51030366`). From 2027, codes are `ISO3.NNN` assigned per parent,
with the government code listed in its own column. `docs/adr/0104`
re-ranks every source value because raw values can be gappy, duplicated
or non-numeric; for 2026 the government codes are the identifiers being
published.

## Decision

`code-refactor` takes `source_codes`:

- `replace` (default): every level is re-ranked, as in `docs/adr/0104`.
- `embed`: a level with a source code column is its parent's code, then
  `delimiter`, then its own source value; `delimiter` may be empty. It
  raises if a row has no source code, or if the delimiter is empty and a
  level's codes differ in length, since the code couldn't be split.
- `copy`: as `replace`, after copying each level's source code column to
  its next free numbered sibling (`adm1_code1`).

With explicit field templates, a level with a name column but no code
column gets one seeded from its names, ranked under its parent by name,
under every mode.

## Consequences

`code-update` can't reconcile against an OLD file coded without a
delimiter, since its format detection splits on one; 2026 change
management follows the government codes instead. A seeded level's
numbers follow alphabetical name order, so they shift when a sibling is
added or renamed. The sister JS app needs the same option to match.
