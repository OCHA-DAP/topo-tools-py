# 0139: `close_notches()` keeps vertices shared with a third unit

## Status

Accepted. Supersedes ADR-0132's endpoint move and enclosed-gap rule.

## Context

Moving a flagged endpoint that the unit also shares with a third unit
drags the unit away from that third unit. Where the unit is a narrow strip
or its border meets a third unit's, this cuts out a wedge no other unit
fills (Oman admin2: six holes up to 0.59 km², none reported), or shifts a
border with the third unit by hundreds of metres.

## Decision

An endpoint touching a unit other than the pair stays put. A gap the fix
encloses counts as enclosed when bounded by the pair and their neighbours,
and merges into whichever of the pair shares more of its border.

## Consequences

Notches starting at a junction of three or more units close only partly
in `close_notches()`. The remaining slot merges, or is left to the
whole-file `coverage_clean()`.
