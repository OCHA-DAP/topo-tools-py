# 0127: code-update numbers below placeholder codes without a delimiter

## Status

Accepted.

## Context

Releases without a delimiter use codes at the top of a level's range as
placeholders: `ET99` for contested areas, `98`/`99` for lakes and towns.
Under `docs/adr/0126`, new codes start above a parent's highest code, so a
parent holding `99` at width 2 has no room for a new child and the run
stops (slv, mwi and eth in the portolan catalog).

## Decision

Without a delimiter, when the next number above a parent's highest code
doesn't fit the level's width, new codes continue above its highest code
below the top 10% of the range (`90` at width 2, `900` at width 3). If
they would reach that cutoff, the run raises `ValueError`. With a
delimiter, new codes always start above the
highest code.

## Consequences

ETH's new regions get `ET17` onward beside `ET99`. A parent whose
regular codes already reach the top 10% still raises and needs a wider
width. A code inside the top 10% is never reissued, since numbering stays
below it.
