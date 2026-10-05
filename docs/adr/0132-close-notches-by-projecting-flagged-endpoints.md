# 0132: Close notches by projecting flagged endpoints

## Status

Accepted. Narrows 0006.

## Context

A notch is a long, thin wedge where two neighbouring units' boundaries run
close together without sharing vertices. `edge-extend` samples points along
each unit's boundary, so the Voronoi cells inside a notch alternate between
the two units and stripe deep into both. 0006 left near-miss mismatches out
of scope, because closing them meant widening `ST_CoverageClean`'s
`snapping_distance`, which re-nodes the whole file.

Fourteen notches were reviewed: three in Burundi admin2, seven in Chile
admin3 and five synthetic deep wedges. Three fixes were compared there:
snapping, projecting endpoints, and a combination of the two. Projection
alone closed the most cases and is the only one that moves just the
flagged vertices. Running `ST_CoverageClean` on a window around each notch
was rejected, since a partial clean can misalign the boundary outside the
window. At catalog scale, 214 notches in 47 portolan layers were reviewed,
leaving out four layers that are known incomplete inputs. Every notch that
closes at 1/10 but not at 1/50 was judged one that should close. Snapping a
moved endpoint to the other unit's nearest vertex was also tried and changed
no outcome.

## Decision

- A notch is a pair of units whose unshared boundary segments lie within
  `NOTCH_SPACING / 8` of each other along at least `NOTCH_MIN_SCORE`
  times `NOTCH_SPACING` (`edge-extend`'s default point spacing), summed
  over both units. Every threshold is relative to that spacing; none is a
  fixed distance.
- An endpoint of a flagged segment moves exactly onto the other unit's
  boundary when the gap is at most 1/10 of the segment's own length,
  inside a window around the notch. Wedges of similar shape get the same
  fix whatever their absolute size.
- A gap that the moved endpoints enclose between the two units, with no
  other unit inside it, merges into the unit that shares more of its
  border. A gap that already existed, or that holds another unit, is left
  alone. Only polygon parts of the rebuilt units are kept.
- The whole-file `coverage_clean()` that already runs after reading the
  input then handles any remaining mismatch. `ST_CoverageClean` never
  runs on a window.
- `topo-detect` reports a `notch` row with `near_length_m`. `topo-clean`
  closes notches before its clean, and marks a notch row fixed only if no
  notch between its two units overlaps it in the output. `edge-extend`
  and `edge-match` close notches when they read their input.

## Consequences

Detection uses only unshared segments and a bbox range join, not the
`ST_Difference` against unioned blobs that ran out of memory in 0006. On
those 47 layers the fix closes 199 of 214 notches and raises no unit pair's
notch score, moving a vertex at most 12 m. The 15 left open stay as `notch`
rows for review, as do short kinks where a closed notch leaves the two
units' vertices a few metres apart. `edge-extend` on Chile admin3 takes
417 s, compared with 380 s without the fix.
