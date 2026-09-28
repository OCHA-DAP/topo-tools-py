---
status: draft
title: "edge-clip"
---

See `docs/reference/README.md` for the MUST/SHOULD/MAY convention, and
`docs/reference/shared.md` for rules `edge-clip` shares with other tools.

## Inputs

- `edge-clip` MUST load the input layer and the overlay layer raw,
  neither coverage-checked nor -cleaned.
- `edge-clip` MUST NOT require or read an `overlay_fid` column on the input features
  layer.
- `edge-clip` MUST accept exactly one input file and exactly one
  overlay file per call, a strict 1:1 primitive (see `docs/adr/0080`);
  batching many input files against one shared overlay load is
  `edge-mosaic`'s job (see `docs/reference/edge_mosaic.md`).
- The output row MUST carry a `source_file` column recording the path of
  the input file it came from.

## Assignment

- `edge-clip` MUST internally assign every input feature to exactly one overlay feature before
  clipping, via `assign-one`'s file-wide majority-vote strategy (see
  `docs/explanation/assign.md`): every input feature is forced onto the one overlay feature
  that wins a majority vote by count, unconditionally, not evaluated per
  input feature. An input feature with zero individual overlap with the winner is not
  dropped at this stage; it still gets clipped against the winner and MAY
  drop later if that clip result is empty (see Clipping).
- A whole input file with no overlap against any overlay feature at all MUST be
  dropped, not clipped against the wrong overlay feature.

## Clipping

- `edge-clip` MUST clip each row to its own `overlay_fid`'s geometry via
  `ST_Intersection`, one distinct `overlay_fid` at a time, each in its own
  spawned OS subprocess.
- Within one `overlay_fid`'s subprocess, `edge-clip` MUST grid-subdivide that
  overlay feature's boundary into small tiles before intersecting once its vertex
  count exceeds an adaptive threshold, sizing the tile grid from that
  overlay feature's own vertex density, and MUST join input features to tiles via bbox
  comparison, never `ST_Intersects`.
- An input feature whose clipped result is empty MUST be dropped from the output,
  not treated as fatal, and MUST be recorded in the issues report as a
  `kind='clip-empty'` row (see Outputs).
- `edge-clip` MUST raise immediately on the first `overlay_fid` whose subprocess
  fails, aborting the whole run rather than skipping just that `overlay_fid`.

## Outputs

- `edge-clip` MUST NOT run the coverage hard gate in `docs/reference/shared.md`
  on its own output: closing seams between clipped pieces is `edge-stitch`'s
  job, not `edge-clip`'s.
- `edge-clip` MUST raise `RuntimeError` if the clipped result has zero rows.
- `edge-clip` MUST export the clipped layer to the output file.
- `edge-clip` MUST export an issues report alongside it, using the shared
  schema in `docs/reference/shared.md`, whenever it has at least one
  `kind='clip-empty'` row (or, when a code join is given, one
  `code-mismatch`/`code-fallback` row); when it would be empty, no file
  MUST be written (and a stale file from a previous run at that path MUST
  be removed).

## Configuration (`api.edge_clip.clip()` / CLI)

- The output path MUST default to the input path with a `_clipped` suffix.
  The issues-report path MUST default to the output path with an `_issues`
  suffix.
- `edge-clip` MUST raise `FileExistsError` if either output path already
  exists and overwriting wasn't requested.
- `step`, if given, MUST be one of `inputs`, `assign`, `edge-clip`, `outputs`;
  any other value MUST raise `ValueError`.
- `edge-clip` MAY accept `match_column`/`overlay_match_column`/`input_match_column`
  to override spatial assignment with an exact code join (see
  `docs/reference/shared.md`, `docs/explanation/assign.md`), adding
  `code-mismatch`/`code-fallback` rows to the issues report alongside any
  `clip-empty` rows.
- `edge-clip` MAY accept `carry_columns` (CLI: `--carry-column`) to copy
  named overlay columns onto every matched input feature (see
  `docs/reference/shared.md`, `docs/adr/0077`).

## Examples

### Example 1: clip an input layer against an overlay layer, explicit output

    topo-tools edge-clip input.parquet adm1.geojson clipped.parquet

### Example 2: custom issues report path

    topo-tools edge-clip input.parquet adm1.geojson clipped.parquet \
      --issues-file clip_report.parquet
