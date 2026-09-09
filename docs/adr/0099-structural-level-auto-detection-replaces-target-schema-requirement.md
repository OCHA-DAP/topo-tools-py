# 0099: Structural level auto-detection replaces the target-schema requirement

## Status

Accepted. Supersedes `docs/adr/0098`'s claim that `package-polygons`
"always takes a target-schema YAML."

## Context

`docs/adr/0098` made `package-polygons` always require a target-schema
YAML (`detect_levels()`, naming-template based). Running it against
`chl_admin3.parquet` failed outright: the file uses `adm{n}_pcode`, not
the bundled schema's `adm{n}_code`, so no column matched any level at
all. Auditing the portolan catalog found this wasn't an isolated naming
mismatch: Qatar's admin2 has no single pcode-shaped column at all (three
same-cardinality columns bracket together instead), South Africa's
admin3/admin4 carry a second ID system per level alongside pcode,
Afghanistan's admin2 has genuine duplicate admin-unit names, and older
COD files use camelCase with language suffixes
(`admin2Name_en`/`admin4Pcode`). A template-matching design would need a
YAML per naming convention, maintained by hand, forever trailing the next
real file that doesn't fit.

`schema-map` already solves this same problem for its own crosswalk
output, using cardinality clustering and containment/embedding evidence
instead of column names. Reusing it here means naming is never the
primary detection signal, only ever a completion step layered on top of
an already-established structural result.

Two further gaps surfaced comparing a predicted admin1 dissolve of
`afg_admin2.parquet` against the catalog's own `afg_admin1.parquet`: the
real file keeps all-NULL alt-language columns (`adm1_name2`,
`adm1_name3`) present under their real level, and carries a genuine
non-NULL `area_sqkm` per admin1 unit that a constant-only dissolve can't
produce (each admin2 row's own `area_sqkm` varies within its admin1
group). The real file also carries ArcGIS export artifacts
(`SHAPE__Length`, `SHAPE__Area`, `bbox`, `objectid`), confirmed unwanted
in any output level.

## Decision

`package-polygons`/`package-points`/`package-lines`/`package`/
`schema-fill` auto-detect every hierarchy level structurally by default
(`core.schema_map._level_columns.detect_level_columns()`, reusing
`_02_map.py`'s own cardinality/containment/embedding matcher via an
extracted `resolve_columns()`), never a hardcoded naming convention or
column count. A `target_schema` YAML, or an inline `--name-field`/
`--code-field` pair, remains available on every one of these tools to
force a specific single column per level instead, for a caller who wants
to override what auto-detection picks.

Once a level's own winning code column is structurally established,
naming completes its family: the column's literal prefix (or suffix) is
swept across the rest of the table to catch every other column sharing
it, all-NULL or not, so a placeholder like `adm1_name2` survives under
its real level's output instead of being dropped for having zero
evidence. A file with no recognizable naming pattern on its winning
column degrades to the pre-completion behavior (no placeholders kept).

`core.dissolve()` groups by the entire structurally-detected cluster for
a level, not one canonical column, so every column genuinely 1:1 with
that level's code survives automatically. This only ever matches
grouping by the canonical column alone when every other cluster member is
functionally dependent on it, which schema-map's own bijection/embedding
evidence already requires before assigning a column to a level;
`verify_functional_cluster()` re-checks this at dissolve time regardless,
raising `ValueError` naming the offending column rather than silently
producing fragmented groups if it doesn't hold.

`core.dissolve()` also changes its column-classification default for
every caller: a column that varies within a group is summed when its
DuckDB type is numeric (previously dropped-with-warning like any other
varying column), covering `area_sqkm` or a population count with no
caller-supplied list. An `aggregations: dict[str, str]` override
(`sum`/`min`/`max`/`avg`/`first`) picks a different function per column
for cases where summing is wrong (a rate, a year, a running maximum).

`is_noise_column()` (already used by `schema-map`/`schema-refactor`) is
reused, not reimplemented, to strip ArcGIS/export-tool artifacts
(`objectid`, `bbox`, `shape_leng`/`shape_area` and their GDAL
collision/DBF-truncated variants) from every output level, including the
finest level's own passthrough, which is no longer a byte-identical copy
of the input as a result.

## Consequences

`target_schema_path`/`name_field`/`code_field` are optional everywhere
they exist; omitting all three triggers structural auto-detection instead
of raising. This is additive for a caller already supplying an explicit
schema. It's breaking for the finest level's own output, which now
excludes ArcGIS artifact columns it previously passed through unchanged,
and for `core.dissolve()`'s default handling of a varying numeric column,
which it now sums instead of dropping (documented in `CHANGELOG.md`).

Verified against the full 394-file portolan admin-polygon corpus (112
countries): zero detection failures, and the whole-cluster group-by
invariant (`COUNT(DISTINCT canonical_code)` equals `COUNT(DISTINCT` the
whole cluster tuple`)`) holds in every one of the 241 coarser levels
checked. Auto-detecting `afg_admin2.parquet` and dissolving to admin1
reproduces the catalog's real `afg_admin1.parquet` column-for-column
(net of the intentionally-dropped ArcGIS/`adm1_ref_name` columns), with
summed `area_sqkm` matching to floating-point rounding (~1e-8 km²).

A structural chain can still fail to reach a file's own finest level when
that level's own identifier doesn't embed into its parent (a flat,
non-hierarchical ID rather than a compound code), observed on Lebanon's
`lbn_admin3.parquet`; this is a distinct, open gap in the underlying
embedding-based chain builder, not something this decision changes.
