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
The ratio alone also merged 53 pieces across the catalogue that a visual
review found the original had drawn as separate lobes, joined to the rest
of the unit only at a pinch point. Telling those apart needs the
pre-extension original, which `edge-clip` and `edge-mosaic` don't have
unless a caller passes it.

## Decision

`core.coverage.merge_detached_parts` runs at the end of
`core.edge_clip._engine.main()`, so `edge-clip`, `edge-match` and
`edge-mosaic` share it:

- Each piece is grouped by the pre-clip part holding its interior point;
  that part's kept piece is its largest piece on the unit's original
  footprint (interior point on an original part, or at least 50% original
  land, `DETACHED_MAX_ORIGINAL_SHARE`).
- A piece under 1% of its kept piece's area (`DETACHED_MERGE_MAX_RATIO`)
  merges into the same-overlay feature it shares the longest edge with, if
  the result stays one connected part, unless the original drew it as a
  lobe: at least 50% original land, with the original land clipped away
  beside it under 0.1 of its area (`DETACHED_MIN_NECK_RATIO`). Without an
  original layer it is only reported; `edge-match` uses its pre-extension
  input, `edge-clip` and `edge-mosaic` take `--original`. No absolute size
  limit applies.
- A destination is a kept piece, a single-part feature, or a piece kept as
  too large.
- Every piece with an edge neighbour, merged or kept, is a `detached-part`
  issue row carrying its geometry, area, width, thinness and that
  neighbour's fid. A piece with no edge neighbour is never changed and isn't
  reported.

## Consequences

Output geometry changes wherever a clip detached a piece. Real land can
move to a neighbour, including across a higher admin line (GNB's Quinhamel
piece moves from Biombo to Cacheu); each move is a `fixed=TRUE` row whose
geometry lets a reviewer undo it. In `edge-mosaic`'s per-file loop, a
neighbour in another input file is never a destination. An isolated piece
stays as an extra part and isn't reported; in `edge-clip` and
`edge-mosaic` these are mostly islands (3,124 in one PHL admin3 run before
this was decided). A small piece whose only neighbour is another small
detached piece is treated as isolated too (PNG v01 admin3's PG120233,
1.08 ha of extension fill).

Across the deepest level of all 157 COD-AB catalogue country versions,
`edge-clip` against `bnda_cty`, with each version's original, changed the
geometry of 2,883 features against the published `matched` layers, all but
10 (LKA v01) named in an issue row, with row counts and attributes
matching.
