# 0110: `schema-map` numbers a varying coarsest level adm1 by default

## Status

Accepted. Refines ADR-0108: `--level` is unchanged, only its omitted default changes.

## Context

Numbering the coarsest level 0 fits a multi-country file, the rarer input. The
common input is a single-country file with no country column (e.g. Cameroon's
region/department/commune files), which came out one level too low.

## Decision

With `level` omitted, a constant coarsest level is 0 and a varying one is 1, and
`schema-map` logs a warning that it assumed one country above the file.
`resolve_columns()`'s internal callers (level detection for
schema-fill/package-*/code-*) keep relative 0-based numbering.

## Consequences

Single-country files map with no flag. A multi-country file, a single-level file
(only its own code/name), or a file missing coarser levels misnumbers silently
apart from the warning and needs `--level N`. A constant non-country column (a
one-region extract) still reads as adm0.
