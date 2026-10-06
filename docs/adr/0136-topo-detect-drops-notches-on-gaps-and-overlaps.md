# 0136: topo-detect drops notches on a reported gap or overlap

## Status

Accepted. Amends 0132's `notch` rows in `topo-detect`.

## Context

0132 defines a notch by unshared boundary segments running close
together. A thin gap or overlap between two units has that shape at its
tips, so `topo-detect` reports one defect twice: as a `gap` or `overlap`
row, and as one or two `notch` rows. On the NLD admin2 demo, 9 of 12
notch rows sit on one of 3 gaps or 2 overlaps.

## Decision

`topo-detect` drops a notch that intersects a reported gap, or an overlap
between the same two units. `detect_notches()` and `close_notches()` are
unchanged, so `edge-extend`, `edge-match` and `topo-clean` close the same
notches.

## Consequences

A notch beside an unrelated gap is also dropped; the gap row still points
reviewers to the spot. Notch keys keep their numbering, so dropped rows
leave holes in it. The sister JS app needs the same filter to match.
