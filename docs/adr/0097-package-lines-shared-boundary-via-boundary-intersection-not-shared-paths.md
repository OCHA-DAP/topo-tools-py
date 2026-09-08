# 0097: `package-lines` builds shared boundaries from `ST_Boundary`/`ST_Intersection`, not a shared-paths function

## Status

Accepted

## Context

`package-lines` needs the geometry two adjacent admin units share along
their common edge. PostGIS has `ST_SharedPaths` for exactly this. This
project's pinned DuckDB spatial extension has no `ST_SharedPaths` and no
`ST_Relate`, confirmed via `docs/how-to/verify-duckdb-function.md`'s lookup
procedure against the installed extension's function catalog.

## Decision

Build the shared segment from primitives that do exist:
`ST_LineMerge(ST_CollectionExtract(ST_Intersection(ST_Boundary(a),
ST_Boundary(b)), 2))` per bbox-prefiltered, `ST_Touches`-confirmed
candidate pair, keeping only the `LineString`/`MultiLineString` component
(`ST_CollectionExtract`'s type `2`) and dropping the point-only
intersection a corner-only touch produces. The exterior ring per fid is
the remainder: `ST_LineMerge(ST_Difference(boundary, own_shared_union))`.

The outer `ST_LineMerge` is required on the shared side too, confirmed
against real portolan boundary data (Senegal admin3, a 125-row country):
`ST_Intersection` of two boundaries returns one `LineString` fragment per
matching edge segment, not one merged line, even where both sides' vertex
sequences exactly coincide along the shared edge. Without it, one touching
pair produced 418 separate 2-point fragments instead of a single merged
line; across a whole country this inflated a 296-pair shared-boundary
network from an expected few hundred rows to 124,333, an over 400x file
size and 15x wall-time regression that only surfaced against real,
many-vertex admin boundaries, since the synthetic test fixtures' simple
squares happened to intersect as a single already-merged segment.

## Consequences

Two whole-boundary `ST_Intersection` calls per touching pair (shared) plus
one `ST_Difference` per fid (exterior) cost more than a single
`ST_SharedPaths` call would, but both operate on already bbox-prefiltered,
part-exploded, whole-fid-boundary inputs, never a global union operand,
matching this project's existing anti-pattern rule for large collection
operands (`docs/adr/0001`, `docs/adr/0090`).
