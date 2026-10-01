# 0121: Code tools stop on a merged or skipped level

## Status

Accepted.

## Context

BHR v01 admin3 has a name-only admin2 level whose names repeat across
admin1 units (5 of 175, e.g. Isa Town under Capital and South), and admin3
names that are block numbers (`'101'`) beside 4-digit codes (`'0101'`).
Containment allows one repeating name, so admin2 never formed a level;
both admin3 columns were code-shaped, so the level had no name, and
bracketing made `adm2_name` its name despite collapsing 499 units to 175.
`code-refactor` took `adm3_name` as the level's code column and
overwrote it, with no error.

A nesting share can't tell a missed level from an attribute column: over
the 53 of 369 `hdx-cod-ab-ai/data` files with a supplemental grouping,
real intermediate levels with parent-local codes (`ago` and `bdi`
`adm2_code`, `pry` `DISTRITO`) nest 11 to 29% by value, while attribute
columns (`edit_par`, `resolution`, `lang`) nest 100%.

## Decision

- When a chain level has no name and two or more code-shaped columns
  that don't embed the parent, a column carrying the target schema's
  `name_field` text and not its `code_field` text (`_name` vs `_code`)
  becomes the name, as long as one code remains.
- `verify_functional_cluster` takes the parent level's code column and
  raises when a member has over `_WINNER_MAX_COLLAPSE_RATIO` fewer
  values than the level's code under each parent.
- `code-refactor` and `code-update` raise in structural mode when
  detection sets any column aside as a supplemental coarser grouping,
  naming the columns and asking for explicit field templates.

## Consequences

Structural coding stops on files with a supplemental attribute column
(`pays`, `edit_par`, `SOURCE`), which then need
`--code-field`/`--name-field`; the `cod-ab` skill always passes them.
Column resolution across all 369 `hdx-cod-ab-ai/data` files is unchanged.
Structural detection still misses intermediate levels whose codes are
local to each parent, and coarser levels above the root (`syr`
`Sub__District`'s `ADM1_*`).
