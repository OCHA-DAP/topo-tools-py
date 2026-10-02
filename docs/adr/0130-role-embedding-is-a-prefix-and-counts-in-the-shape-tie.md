# 0130: A role embedding is a prefix, and counts in the shape tie

## Status

Accepted.

## Context

`_assign_chain_roles()` makes a chain column a `code` when it embeds a
column at its parent level, or when most of its values contain a digit.
The embedding test was `contains(child, parent)`, with `_embeds()`'s one
tolerated exception. The root group also collects constant attribute
columns, so a short constant can sit inside names by chance. In SVK
admin1, `lang` is `sk`: seven of eight unit names contain it
(`Nitriansky kraj`, `Trnavský kraj`), `Košický kraj` was the tolerated
exception, and `adm1_name` and `adm1_ref_name` resolved as codes. The
level had no name, so `resolve_levels()` refused the layer.

`_break_shape_tie()` renames code-shaped columns whose names carry the
target schema's name marker, when a level has no name. It counted only
the code-shaped columns that don't embed the parent, both for the tie
(two or more) and for the code that must remain. In QAT admin3 the adm2
names end in a number (`Al Ghuwairiya 76`), so `adm2_name` and
`adm2_name1` were code-shaped beside an embedding `adm2_pcode`. Renaming
both would leave no shape-only code, so the tie was never broken and
level 2 had no name.

## Decision

Role assignment tests embedding with `starts_with(child, parent)`, the
shape hierarchical codes take (`SK023` under `SK`). Chain building keeps
`contains()`. The shape tie counts every `code` column of the level,
embedding ones included, and a code must still remain after renaming.

## Consequences

Across the 281 latest original admin1 to admin5 portolan layers, column
roles change for QAT admin3 and SVK admin1 and admin2 only, each a name
column resolving as a name. SVK admin1 passes level resolution. A code
that embeds its parent's code mid-value (`21SVK023`) is a code by value
shape alone.
