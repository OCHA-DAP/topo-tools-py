# 0125: code-create strips parent prefixes and allows no delimiter

## Status

Accepted. Amends `docs/adr/0122`.

## Context

Government codes come either local to each level (`11`, `22`, `33`) or
already containing the parent's code (`11`, `1122`, `112233`), and an
existing p-code (`AF34`, `AF3404`) has the same shape as the second.
Embedding the second shape as-is doubles the prefix (`XY111122`).
Sources with no government codes (another organisation's IDs, or none)
still need country-code-style codes with no delimiter.

## Decision

- Under `embed`, when every source code at a level starts with its
  parent's source code (or `root_code`, at level 1) and is longer than
  it, the prefix is removed before embedding. When only some codes do,
  `embed` raises `ValueError`.
- `delimiter` may be empty under every `source_codes` mode.
- With an empty delimiter and a fixed width, a level that overflows its
  width raises `ValueError`, since a longer tail can't be split.

## Consequences

Both government code shapes give the same p-code, and existing p-codes
fed back in come out unchanged. A local code that happens to start with
its parent's code on every row is read as hierarchical. Another
organisation's IDs that carry no prefix (FAO GAUL's plain numbers) pass
through `embed` unnoticed, so the caller decides whether the codes are
the government's.
