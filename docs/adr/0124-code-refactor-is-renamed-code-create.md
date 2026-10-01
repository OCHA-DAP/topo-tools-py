# 0124: code-refactor is renamed code-create

## Status

Accepted.

## Context

Choosing between the two code tools comes down to one question: is there
a previous release to carry codes from? `code-refactor` didn't say that
it creates codes from scratch (fresh numbers, or government codes
embedded), and "refactor" reads as a code-maintenance term.

## Decision

The tool is `code-create` (`api.code_create`, `core.code_create`, CLI
`code-create`), with no alias. `code-update` keeps its name.

## Consequences

Scripts and docs calling `code-refactor` must switch to `code-create`.
Earlier ADRs keep the name `code-refactor`. The sister JS app needs the
same rename to match.
