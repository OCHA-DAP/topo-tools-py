# 0102: next-available code is derived from live codes, not a persisted registry

## Status

Accepted.

## Context

Both `code-refactor` (a cold-start cascade) and `code-update` (a
per-level batch of new-code requests, `docs/explanation/code_update.md`)
need to pick a fresh, unused integer tail under a given parent. A
persisted, ever-growing registry of every integer ever issued (even after
a unit was later removed) would guarantee no historical number is ever
reissued, but it is external state a caller has to create, maintain, and
keep in sync with the dataset by hand, and there is no natural home for
it in either tool's single-file-pair, single-call design.

## Decision

`next_available_integer()` (`core.code`) derives a parent's next integer
purely from the `existing_codes` list it's given at call time, the codes
genuinely live in the run producing output right now, never a separate
persisted file. `code-update` seeds this with exactly that level's own
just-computed retained (`unchanged`/`renamed`) set, so a code retired
this same run (a `merge`'s two old codes, a `removed` unit's own code) is
immediately eligible for reuse by an unrelated new/split/merge/created
unit at the same level, same run.

## Consequences

Accepted correctness trade-off: if a code was removed while a numerically
higher sibling code was still live, and that higher sibling is also later
removed in a subsequent run, a live-max-only computation can in theory
re-derive a "next available" integer below a number used earlier in the
dataset's own history. This is a deliberate, documented limitation
(`docs/explanation/code.md`, `docs/reference/shared.md`), not a bug to
silently work around with hidden state: a caller who needs strict
historical non-reuse guarantees must track that externally.
