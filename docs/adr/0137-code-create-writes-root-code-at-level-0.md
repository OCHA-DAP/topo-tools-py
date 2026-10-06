# 0137: code-create and code-update write the root code at level 0

## Status

Accepted.

## Context

Every code `code-create` assigns starts with `root_code`, so every coded
layer has one level 0 unit. A layer coded without a level 0 column has
nothing for `package` to dissolve into an admin0 output or to name.

## Decision

With a code template, `code-create` and `code-update` write `root_code`
into level 0's code column (the template at `n=0`) on every row. A missing
column is added after level 0's name column, else after level 1's columns.
Structural detection writes no level 0, since no level 0 column name
follows from the data.

## Consequences

A template run always outputs a level 0 code column, and `root_code` stays
opaque. A structural run that needs one passes the templates.
