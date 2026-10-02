# 0128: blank-code and name-conflict move to code-detect

## Status

Accepted.

## Context

`validate` runs one detect tool per COD-AB phase against a single layer,
each writing its own report. `name-detect` reported two code defects
alongside its name checks: `blank-code` (a unit with no code) and
`name-conflict` (one code with more than one name). With a `code-detect`
tool for phase 4, keeping them in `name-detect` would split code defects
across two reports, or report them twice.

## Decision

`code-detect` reports `blank-code` and `name-conflict`, with the same SQL
and reasons. `name-detect` drops both and still skips uncoded units in
every other check, so a unit with no code appears in no name finding.

## Consequences

`name-detect`'s report no longer carries either kind; a caller relying on
them runs `code-detect` (or `validate`). `name-clean` is unaffected: it
fixes neither kind. A name that differs between two rows of one code is
now a code finding, read in the codes phase before names are reviewed.
