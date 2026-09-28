# 0115: schema-refactor follows the crosswalk's row order

## Status

Accepted. Supersedes ADR-0111's column order for `schema-refactor` only.
Geometry first and the row sort stand.

## Context

ADR-0111 ordered `schema-refactor`'s columns by the
`name_field`/`code_field` templates, whatever the crosswalk's row order,
because following row order let swapped targets (`adm3_name`/`adm3_name1`)
come out in the wrong order (#75). That left no way to choose another
layout (#112). An integer `output_order` column was considered and
rejected: casual users edit the crosswalk in a spreadsheet, where moving
rows is the natural way to reorder and a number column is easy to get
wrong.

## Decision

`schema-refactor` writes columns in crosswalk row order, after `geometry`.
It logs a warning, without reordering, when a column's numbered siblings
aren't in numeric order after it, which catches the #75 swap. `schema-map`
writes rows in template order, so an unedited crosswalk gives nearly the
template layout. `schema-crosswalk` and `schema-join` keep template order.

## Consequences

Reordering is a row move in any editor. Sorting the crosswalk to review it
(by `unique_count`, say) also reorders the output, with no warning unless
it separates siblings. An unedited crosswalk doesn't place a level's other
columns between its names and codes, and it puts kept unmatched columns
after every level.
