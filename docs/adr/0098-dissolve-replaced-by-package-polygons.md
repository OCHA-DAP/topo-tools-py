# 0098: `dissolve` replaced by `package-polygons`, `--group-by` removed

## Status

Superseded by `docs/adr/0099` (target-schema YAML is no longer required;
structural auto-detection is the default, the YAML/`--name-field`/
`--code-field` pair is now an opt-in override). The `dissolve`-removal/
`package-polygons`-replacement decision itself is unaffected.

## Context

`dissolve` took a single `--group-by` column list and produced one
coarser level per call, with no knowledge of an admin hierarchy. A web-map
cartography workflow needs every coarser level (admin2 down through
admin0) from one finest-level input, plus matching point and line
derivatives keyed off the same hierarchy. Calling `dissolve` once per
level, by hand, with a manually-typed `--group-by` each time, duplicates
exactly the level-detection logic `schema-map`'s `detect_levels()` already
provides for `schema-fill`.

## Decision

`package-polygons` replaces `dissolve` as the CLI/API-facing tool: it
always takes a target-schema YAML, always auto-detects every present
level via `detect_levels()`, and always produces one output per level in
a single call. `--group-by` (arbitrary-column grouping, not tied to any
admin hierarchy) is removed entirely rather than kept alongside the new
mode, since its only real use was hand-driving the same per-level loop
`package-polygons` now does automatically. The underlying `core.dissolve`
primitive (`_01_inputs.py`/`_02_dissolve.py`/`_03_outputs.py`) is
unchanged and unrenamed: `package-polygons`, `package-points`, and
`package-lines` all call its stage functions directly, the same
direct-stage-reuse pattern `edge-match` uses on `edge-extend`.

## Consequences

`dissolve --group-by X` (API `dissolve()`) no longer exists; a caller
building a `schema-map` target-schema YAML for their column convention
and running `package-polygons` gets every coarser level in one call
instead. This is a breaking CLI/API change, documented in `CHANGELOG.md`.
The old tool's module, tests, and docs (`topo_tools/api/dissolve.py`,
`tests/test_dissolve.py`, `docs/reference/dissolve.md`,
`docs/explanation/dissolve.md`, `docs/tutorials/dissolve.md`) are deleted
outright, the same convention `docs/adr/0075` established for
`dissolve-hierarchy`.
