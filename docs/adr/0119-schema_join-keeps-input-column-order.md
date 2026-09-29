# 0119: `schema-join` keeps the input layer's column order

## Status

Accepted. Supersedes ADR-0115's template order for `schema-join` only.

## Context

`schema-join` reordered every column by template, moving a per-level extra
such as `adm2_type` ahead of `adm2_code`. That undid the order a user set by
moving crosswalk rows in `schema-map`.

## Decision

`schema-join` keeps the input layer's columns in input order. A numbered
sibling it adds goes right after its own column's family. A column absent
from the input layer goes after every input column, in template order. The
row sort by the deepest level's code stands.

## Consequences

Crosswalk order holds through `schema-join`. An input layer that wasn't
through `schema-map` keeps its own order rather than getting template order.
