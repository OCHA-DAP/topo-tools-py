# 0103: `code-update` re-derives each NEW unit's parent spatially, never from an embedded column

## Status

Accepted.

## Context

A NEW candidate's raw attribute columns typically still carry some kind
of parent reference (a source `GID_1`-shaped column, or simply the row's
own position under a coarser grouping in the file). Trusting that column
directly to determine which coarser unit a NEW unit belongs to would be
the cheapest implementation, requiring no spatial computation at all.

That reference goes stale exactly when it matters most: when the coarser
unit was itself split, merged, or relocated this same version, the very
cases `code-update` exists to classify correctly. A raw embedded column
has no way to reflect a change that happened during the same version
transition it's describing.

## Decision

For every level finer than the coarsest, `code-update`'s `_05_reparent`
stage re-derives each NEW unit's true current parent spatially, against
the immediately-coarser level's NEW, already-dissolved units, via
`core.assign.assign_many()` (per-child best overlap, not a shared
majority vote). The re-derived parent code, not any raw source column, is
what every downstream code-assignment decision at that level is scoped
under.

## Consequences

`assign_many()` runs once per finer level per `code-update` call, an
added spatial join beyond what `core.change`'s own classification already
performs. A NEW unit with genuinely ambiguous overlap against the
coarser level (near-equal overlap with two neighboring parents) resolves
to whichever `assign_many()` picks as the single best match, the same
resolution behavior every other `core.assign` caller in this repo
already accepts.
