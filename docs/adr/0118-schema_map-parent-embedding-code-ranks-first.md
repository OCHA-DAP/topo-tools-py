# 0118: `schema-map` ranks a parent-embedding code first among same-level codes

## Status

Accepted. Refines ADR-0056's numbering order for `code` companions.

## Context

ADR-0056 numbers same-level companions by source-column order. A surrogate
integer ID placed before the real p-code (GRASS's `cat` in AFG COD-AB v04)
took the bare `adm1_code`, and the p-code became `adm1_code1`.

## Decision

Among a level's `code` members, one that textually contains its resolved
parent's code ranks first, and source-column order breaks ties. Name members
keep source-column order. `cat` joins `NOISE_COLUMNS`.

## Consequences

A p-code outranks an unrelated ID whenever the parent's code column is in the
file. When it isn't, source-column order still decides.
