# 0133: `edge-match`/`edge-mosaic` report only gaps inside their clip targets

## Status

Accepted. Narrows 0035's reporting rule; its raise threshold is unchanged.

## Context

0035 reports every leftover gap wider than `SNAP_TOLERANCE` as a `gap`
row, since a wide gap may be a real hole in the overlay layer (Lesotho
inside South Africa). Matching NLD admin2 into admin1 per polygon wrote 22
`gap` rows, all holes the overlay layer itself has or areas no input was
clipped into, burying any real defect.

## Decision

A leftover gap gets a `gap` row and a warning only when its interior point
(`ST_PointOnSurface`) falls inside an overlay polygon the output was
clipped to: `edge-match`'s assigned overlay polygons other than the
passthrough group, `edge-mosaic`'s assign-one winners. The test is a
bbox-prefiltered point-in-polygon join, shared with topo-tools-js.

## Consequences

The NLD run reports 0 `gap` rows. An overlay polygon whose group was
dropped still counts as a clip target, so a gap there is still reported.
