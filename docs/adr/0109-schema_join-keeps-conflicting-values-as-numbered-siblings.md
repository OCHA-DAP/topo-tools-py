# 0109: `schema-join` keeps a conflicting parent value as a numbered sibling column

## Status

Accepted.

## Context

`schema-join` copies a parent layer's hierarchy columns onto each child it
overlaps most (issue #67). A child often already carries some of those columns,
e.g. its own `adm2_name`, and the two layers can disagree, such as a name
spelled with an accent in one layer and without it in the other. Neither side
is reliably correct, and choosing one belongs to a later review step, the same
way two native source columns for one level are kept side by side as
`adm3_name`/`adm3_name1`.

## Decision

For each parent hierarchy column already present on the child:

- identical on every matched row: skipped, the child's column stays as-is;
- different on any matched row: the child's column stays untouched and the
  parent's values are added as the next free numbered sibling (`adm2_name1`,
  then `adm2_name2` if taken), with one `value-mismatch` issue row per child
  where both values are non-NULL.

This applies to names and codes alike. `schema-join` never raises on a
conflicting value and never overwrites a child's own value.

## Consequences

A run never stops on a spelling variant, and every disagreement stays visible
in both the output and the issues file. A caller has to pick between sibling
columns downstream before packaging. A child that overlaps no parent is
excluded from the comparison, so it never triggers a sibling column on its own.
