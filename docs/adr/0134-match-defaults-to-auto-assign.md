# 0134: `edge-match` defaults to `--assign auto`

## Status

Accepted. Supersedes 0082's assign-one default for `edge-match`; its
assign-one semantics are unchanged.

## Context

0082 made `assign-one` `edge-match`'s default, with `assign-many` behind
`--per-feature`, because a CLI run gives no visual feedback and a wrong
automatic pick would go unnoticed. A layer spanning many overlay polygons
(NLD admin2 into admin1, 78 of 342 polygons overlapping the winner) loses
most of its polygons under assign-one until the user finds the flag.
topo-tools-js defaults to an auto mode for this case.

## Decision

`edge-match` takes `--assign auto|one|many`, defaulting to `auto`, with the
same values as topo-tools-js. `auto` runs assign-one's majority vote and
switches to `assign-many` when fewer than half the assigned input polygons
overlap the winner. Every run logs the mode used, with the overlap count
and the flag that forces the other mode. A multi-file call runs `auto` as
`one`, and `many` raises there (0084).

## Consequences

The NLD pair runs as `many` with no flags. A one-province file with a few
offshore strays runs as `one`. `--per-feature` is removed; scripts using
it pass `--assign many`. `auto` pays for the majority vote before an
`assign-many` run, which is small next to per-group extension.
