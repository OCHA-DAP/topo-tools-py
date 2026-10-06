---
title: "topo-detect"
sidebar:
  order: 3
  badge:
    text: Draft
    variant: caution
---

## Inputs

- `topo-detect` MUST read the input and reproject it to EPSG:4326 without
  correcting any topology defects first, so the issues stage sees the
  original, unmodified geometry.

## Detecting gaps, overlaps and micro-polygons

- `topo-detect` MUST report every fully-enclosed hole in the combined shape of
  all input polygons as a gap, regardless of its size. An open,
  non-enclosed inlet between two polygons MUST NOT be reported as a gap.
- `topo-detect` MUST report every case where two polygons' interiors genuinely
  overlap, or one fully contains the other, as an overlap, regardless of
  its size, whenever the input has any coverage violation at all. If the
  input has no coverage violations, `topo-detect` MUST report zero overlaps
  without running the overlap check. Two polygons that only share a
  boundary edge MUST NOT be reported as an overlap.
- `topo-detect` MUST report every micro-polygon part as a `micro-polygon`, identifying the unit
  it belongs to.
- `topo-detect` MUST report every pair of units whose unshared boundaries
  run within `NOTCH_SPACING / 8` of each other along at least
  `NOTCH_MIN_SCORE` spacings as a `notch`, identifying both units and the
  close-running length, except a notch that intersects a reported gap, or
  an overlap between the same two units, which MUST NOT be reported.
- If detecting one kind of defect fails, `topo-detect` MUST still report the
  other kinds rather than failing entirely.
- The issues report MUST list, for every defect: a unique key, its kind
  (gap, overlap, micro-polygon or notch), its area, its width, and its geometry.
  A gap entry MUST also carry a compactness score (how thin and elongated
  its shape is, as opposed to round and plausible); an overlap entry MUST
  also identify the two units involved. Neither MUST appear on the other
  kinds' entries.

## Outputs

- `topo-detect` performs no topology hard gate at all; it is a read-only
  inspection, not a fix.
- `topo-detect` MUST always produce an issues report, even when the input had
  zero defects.

## Configuration (`api.topo_detect.detect()` / CLI)

- `topo-detect` MUST process exactly one input file per call.
- The issues-report path MUST default to the input path with an
  `_issues` suffix.
- `topo-detect` MUST raise `FileExistsError` if the output path already
  exists and overwriting wasn't requested.
- `step`, if given, MUST be one of `inputs`, `issues`, `outputs`; any
  other value MUST raise `ValueError`.

## Examples

### Example 1: basic run, output name chosen automatically

    topo-tools topo-detect example.geojson

### Example 2: explicit output

    topo-tools topo-detect example.gpkg example_issues.gpkg
