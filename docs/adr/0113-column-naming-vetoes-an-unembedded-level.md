# 0113: Column naming vetoes an unembedded level

## Status

Accepted.

## Context

`schema-map` builds the admin chain from structure alone: containment,
code embedding, and the constant-root exemption. A coarser grouping that
nests a level perfectly without the level's codes embedding it is
structurally identical to a real level: Nigeria's senatorial districts
over LGAs, Burkina Faso's `adm1_pcode_old` over current regions, and
Myanmar's D-coded districts (a real level) all look the same. Data alone
can't separate them.

## Decision

Column naming may veto a chain level, never add one. A non-root level
linked to its child only by an unembedded edge is dropped when both of the
following hold. The naming the chain's levels share (the longest common
prefix and suffix across one column per level, each level keeping a
distinct, non-empty middle) must grow when the level is removed. It must
also grow more than when the level's child is removed instead. The
parent must still nest the child directly. The dropped group is reported
as `supplemental, superset of level {k}`.

## Consequences

The rule was checked on 757 portolan and raw-schema files and 267 CODs
original layers. It fixes Nigeria admin2, and Burkina Faso admin1/admin2
and their originals. It also stops audit or old-code columns from taking
a level in Afghanistan, Angola, Mozambique, Viet Nam and Central African
Republic originals. It demotes a real tier where unrelated columns share
naming by chance: GRID3 DRC health areas' `antenne` becomes supplemental
because `zs_uid`/`as_uid` share `s_uid`. Such a tier is still reported,
not lost. A naming signal must never be extended into positive evidence
for a level or role.
