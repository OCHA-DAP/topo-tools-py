# 0111: Geometry first, and schema tools order columns and rows by template

## Status

Accepted.

## Context

Every tool wrote `geometry` last except `schema-refactor`, which wrote it
first, and the schema tools wrote admin columns in crosswalk-row or join
order with rows unsorted (#75). No standard sets column position: the
GeoParquet spec and geoparquet-io cover only row order (spatial, Hilbert),
GeoPackage and FileGDB writers put the feature id and geometry first, and a
Shapefile has no geometry column at all. Structural level detection misread
code/name roles on small files and pulled row-unique numeric columns
(`area_sqkm`, `center_lat`) into a level on real ones.

## Decision

Every geometry output writes `geometry` first, with no added index column.
The schema tools order columns by the `name_field`/`code_field` templates,
via `core.admin_columns`, a neutral leaf, so `schema-refactor` stays
independent of `schema-map`. Rows are sorted by the deepest level's code as
text, not in Hilbert order, since admin units have a natural order.

## Consequences

A reader of any tool's output by column position sees a new layout.
Ordering needs template-named columns: raw source names keep input order,
and a non-default schema needs `--name-field`/`--code-field`. Unpadded text codes
sort as text (`X1, X10, X2`); integer code columns sort numerically. Rows aren't spatially ordered, which costs
nothing within a single row group.
