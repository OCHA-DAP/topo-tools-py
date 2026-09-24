# 0108: `schema-map` takes an optional `--level` anchoring the finest level

## Status

Accepted. Refines ADR-0058 and ADR-0066: relative-rank numbering stays the default.

## Context

A file with no country column gets its coarsest level numbered `adm0`, so every
level in a sub-national file comes out one or more too low (issue #65). Structure
alone can't tell a real admin0 from a coarsest-in-file level, and a value rule
(non-constant coarsest means admin1) would misnumber multi-country files.

## Decision

`--level N` (`level=N`) numbers the finest resolved level `N` and each coarser one
by nesting depth from there. It is optional; omitted, numbering stays relative
(0 = coarsest). A folded constant root is still excluded. A `level` too small for
the discovered depth raises `ValueError`. It restores none of `own_level`'s
template fallback or gap rows.

## Consequences

A caller that knows the file's own level gets correct numbers with no crosswalk
edit. A file with a skipped level (e.g. admin3 and admin1 columns, no admin2)
still numbers its coarser level one too deep.
