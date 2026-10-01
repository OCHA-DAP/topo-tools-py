# 0123: Code min_width per level or auto

## Status

Accepted. Amends `docs/adr/0101`'s single `min_width`.

## Context

One `min_width` for every level can't express a scheme whose levels pad
differently (2-digit admin1, 4-digit admin3). Under `embed` with an
empty delimiter, a numbered level must also keep one length, and a
parent that outgrows a fixed width breaks that. `code-update` detected
one width pooled across levels, so it miscoded an OLD file whose levels
differ.

## Decision

- `min_width` is one width (`3`), one width per numbered level, coarsest
  first (`2,2,4`, exactly one entry per level, else `ValueError`), or
  `auto`.
- `auto` pads every new code at a level to the widest tail that level
  needs, retained codes included, so the level never overflows and has
  no overflow report.
- `detect_code_format()` takes the most common width at each component
  position, returning one width when every level agrees.
- `code-refactor` and `code-update` both accept all three forms.

## Consequences

Under `auto`, a level's width can change between releases as its
largest parent grows, changing every code at that level. A width list
needs each level's child counts known in advance. The sister JS app
needs the same forms to match.
