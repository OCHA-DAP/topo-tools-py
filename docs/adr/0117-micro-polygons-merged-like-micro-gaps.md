# 0117: Micro-polygons are merged like micro gaps are filled

## Status

Accepted.

## Context

topo-tools-js's Clip wrote an extra ~1e-13° wide feature for NLD gemeenten
against provincies: DuckDB-WASM's PROJ and native PROJ disagree by up to
5.7e-14° on reprojected vertices, so a border that only touches natively
overlaps by a sliver in the browser. Micro gaps (at most `SNAP_TOLERANCE`
wide) were already a hard-gate defect, but a polygon part of the same width
was not. Multipolygons pairing a large part with tolerance-scale fragments
are almost always digitization or processing errors.

Testing `ST_CoverageClean(geoms, 1e-8, 1e-8)`, in native DuckDB spatial and
DuckDB-WASM alike, showed it absorbs overlap slivers, touching fragments and
detached islands, but returns a feature that is entirely micro as an EMPTY
geometry, which `coverage_clean` kept as an empty row. The
`ST_CoverageInvalidEdges_Agg` trigger that decides whether to clean an input
doesn't flag a micro feature that only touches its neighbours.

## Decision

A micro-polygon is a polygon part whose maximum inscribed circle is at most
`SNAP_TOLERANCE` across, the micro-gap measure. `2 * area / perimeter` bounds
that diameter from below and skips the costly call for every wide part.

`core.coverage` owns the rule for both ports:

- `has_micro_polygons`/`check_micro_polygons`, folded into
  `has_valid_topology`/`check_valid_topology`, so every hard gate and the
  input auto-clean trigger catch them.
- `merge_micro_polygons` merges each micro part into the feature whose
  non-micro part overlaps its `SNAP_TOLERANCE` buffer most (ties to lowest
  fid, its own feature included), drops it when that overlap is zero, and
  removes a feature left with no parts. Unaffected rows pass through
  unchanged. Each part becomes a `micro-polygon` issue row.
- `coverage_clean` runs the merge before `ST_CoverageClean`, so the EMPTY row
  never arises. That covers `edge-extend`, `edge-stitch` (and so
  `edge-match`/`edge-mosaic`), `topo-clean` and every auto-cleaned input.
- Paths with no clean call it directly: `edge-clip`'s clipped output,
  `topo-clean`'s output (for runs that skip the clean), and
  `package-polygons`/`package-points`/`package-lines` input.
- `topo-detect` reports micro-polygons unfixed.

`change` gets no extra call: its inputs are auto-cleaned, and its overlay
already drops intersections below `SNAP_TOLERANCE` squared.

## Consequences

A layer with micro features loses those rows, reported in the issues file
where the tool writes one; `edge-stitch` on its own tiny-gap test fixture
writes two features, not four. Outputs from `package-points` and
`package-lines`, which write no issues file, only log the count. The merge
buffers and intersects only micro parts, so its cost scales with the number
of defects, not layer size.
