# 0135: embed pads integer source codes

## Status

Accepted. Amends `docs/adr/0122`'s length check under `embed`.

## Context

Some source code columns are integers (`1` to `11` for admin1, `101` to
`1105` for admin2). Under `embed` with an empty delimiter, their lengths
differ, so `docs/adr/0122` raises. Zero-padding an integer changes how it
is written, not its value, so the result still embeds the source's own
identifier. `docs/adr/0123` pads codes seeded from names, never source
codes.

## Decision

With an empty delimiter, every level's part of an embedded code has one
width, or the run raises. An integer level's codes either repeat their
parent's code (`805` under `8`) or are numbered within the parent (`5`,
`110`, `1100` under `11`). They repeat it only when every code starts with
the parent's code and the remainders share one width; that prefix is then
stripped as in `docs/adr/0122`. Otherwise the codes are kept whole, with an
info log naming the level, since stripping `110` and `1100` would leave
`0` and `00`. The remaining part is left-padded with zeros to the larger of
the level's `min_width` and its widest part, never truncated. A text level
is never padded and still raises on mixed lengths or a partial prefix
match. With a delimiter, integer codes are embedded unpadded.

## Consequences

A level's width can grow between releases when a new source code is
longer, changing every code at that level, as `auto` already does in
`docs/adr/0123`. The sister JS app needs the same padding to match.
