# 0120: Clip-detached pieces merge into their longest-edge neighbour

## Status

Accepted.

## Context

Clipping an extended feature to its overlay feature can cut one of its
parts into several pieces. AFG v04 admin2's Barmal left `edge-match` with
two extra parts (1,431 and 278 m²) touching only its neighbour and the
country edge; ETH v04 admin1's Tigray with a seven-piece strip (0.04 to
2 km²) along ET99. Both are wider than `SNAP_TOLERANCE`, so the
micro-polygon merge (`docs/adr/0117`) kept them, and no issue row
reported them.

Measuring each piece against its whole feature flagged half of a genuinely
split island, so pieces are measured per source part. An absolute cap on
area (1 ha) or width (350 m) was tested against AFG, ETH and the West
Africa cluster: no single value merged the Tigray strip without also
merging compact pieces of real land, and every value depended on the
country's scale. Most pieces the 1% ratio merges on its own are Voronoi
extension fill, owned arbitrarily in the first place; a few (GNB's
Quinhamel piece, 1.16 km², and the Tigray strip) are real source land.

## Decision

`core.coverage.merge_detached_parts` runs at the end of
`core.edge_clip._engine.main()`, so `edge-clip`, `edge-match` and
`edge-mosaic` share it:

- Each piece is grouped by the source part it overlaps most (`edge-match`
  passes its pre-extension input); the piece overlapping that part most is
  its main piece.
- A piece under 1% of its main piece's area (`DETACHED_MERGE_MAX_RATIO`)
  merges into the same-overlay feature it shares the longest edge with, if
  the result stays one connected part. No absolute size limit applies.
- Every piece, merged or kept, is a `detached-part` issue row carrying its
  geometry, area, width and thinness.

## Consequences

Output geometry changes wherever a clip detached a piece. Real land can
move to a neighbour, including across a higher admin line (GNB's Quinhamel
piece moves from Biombo to Cacheu); each move is a `fixed=TRUE` row whose
geometry lets a reviewer undo it. In `edge-mosaic`'s per-file loop, a
neighbour in another input file is never a destination. An isolated piece
stays as an extra part, reported as `kept: no neighbour`.
