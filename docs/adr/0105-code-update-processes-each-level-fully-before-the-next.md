# 0105: `code-update` processes each level fully before the next, not stage-major

## Status

Accepted.

## Context

At-scale testing against a real, multi-level, archipelagic dataset
(Philippines admin1-3, v02->v03) hit `OutOfMemoryException` inside
`_04_classify`'s overlap join. A stage-major orchestration (every level's
`dissolve` step completing before `classify` starts for any level, then
every level's `classify` before `reparent`, and so on) kept every level's
dissolved OLD/NEW geometry tables resident simultaneously from the
`dissolve` stage through to `outputs`: a `--debug`/`--step` diagnostic run
showed a 1.7 GB persisted `.duckdb` file after just `inputs`+`dissolve`
alone, before `classify` had run at all, confirmed as the dominant driver
once ruled out as a per-query blowup (a direct re-run of the overlap
join's bbox-prefiltered `ST_Intersects` step against the same dissolved
tables produced only ~12,500 candidate pairs, no combinatorial explosion).

## Decision

Dissolve, classify, reparent, and assign now run as one per-level loop,
ascending, instead of four stages each looping over every level in turn.
Each level's own `_dsl_{n}_a` (OLD) is dropped once that level's `assign`
step has read it; `_dsl_{n}_b` (NEW) is kept resident one extra iteration,
since the next level's `reparent` step needs it as the parent geometry,
then dropped once that next level's `reparent` has run. `_07_outputs`
never needs a dissolve table at all: each level's `fid -> raw column
value` mapping is captured into a small Python dict right after that
level's own dissolve, before its `_dsl_{n}_b` would otherwise be dropped.

The CLI's `--step` granularity collapses from `inputs`, `levels`,
`dissolve`, `classify`, `reparent`, `assign`, `outputs` to `inputs`,
`levels`, `process`, `outputs`: `dissolve`/`classify`/`reparent`/`assign`
are no longer independently resumable stages, since none of them holds
memory-boundedness on its own once interleaved per level.

## Consequences

Peak resident geometry across the four middle stages is now bounded by
roughly two levels' dissolved tables at once, not all levels
simultaneously. Confirmed via re-run: DuckDB's own tracked table memory
stayed under ~1.3 GB while processing the first level alone, where the
old stage-major path had already reached 1.7 GB before any classify work
began.

This did not fully resolve the original OOM. Re-running the same PHL pair
still crashed, now at the first level's own `classify` step, because
`_01_inputs`'s coverage-cleaning of the two full finest-level files
(`core.io.read_reproject_and_clean()`, shared by every tool that reads a
layer) itself peaked at ~5-8 GB on this dataset, before any per-level work
starts. That cost is orthogonal to this decision, not specific to
`code-update`'s own stage architecture, and is left undocumented as a
fix; a memory-constrained run against a similarly large/complex input MAY
still exceed a 2-4 GB budget on `inputs` alone.
