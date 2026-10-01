# 0126: code-update never reuses a code and reads codes without a delimiter

## Status

Accepted. Supersedes `docs/adr/0102`.

## Context

Releases keep ISO2-style codes with no delimiter (`SN0101`) until a bulk
migration to `ISO3.NNN`, so `code-update` meets both formats in a previous
release. Under `docs/adr/0102`, a code retired in a run could go to a
different unit in the same run. A previous release's names-only level has
no code column to carry over.

## Decision

- New numbers start above every code each parent had in OLD, retired
  codes included.
- Without a delimiter, the format is detected from OLD's per-level code
  columns: the root is level 1's leading non-digit run, and each level's
  width is the length it adds to its parent's code. `min_width='auto'`
  with no delimiter raises `ValueError`.
- With explicit templates, a level-0 code column is left untouched, and a
  NEW level with only a name column is seeded from its names.
- Strict or lenient follows the code format: without a delimiter, a
  `modified` 1:1 match keeps its code; with one, it gets a new code.

## Consequences

No code is reissued across consecutive releases. A code retired two or
more releases back isn't tracked. Codes without a delimiter keep
continuity through re-digitising, but don't promise identical geometry.
The sister JS app needs the same changes.
