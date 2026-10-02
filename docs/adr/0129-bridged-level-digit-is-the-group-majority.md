# 0129: A bridged level's naming digit is its group's majority

## Status

Accepted.

## Context

`_bridged_edges()` keeps a level in the chain without an embedding of
its own when containment holds on both sides, a direct skip across it
embeds, and its naming digit sits between its neighbours'. Each group's
digit came from `_group_digit()`, which returned a digit only when every
column in the group agreed.

The root group also collects constant attribute columns. In KGZ and LBN
admin3 it holds `adm0_*` beside `lang1` and `lang2`, so it had no digit.
The `adm0` to `adm2` skip embeds (`KG` in `KG05258000000`, `LB` in
`LB11`), but with no root digit the bridge never formed. adm1 to adm2
doesn't embed in either file: KGZ codes are zero-padded to a fixed width
(`KG05000000000`, `KG05258000000`), and in LBN the Akkar and
Baalbek-Hermel districts keep their earlier governorates' codes
(`LB7`, `LB51`). The chain then ran adm1 to adm3, and cardinality
bracketing folded every `adm2_*` column into level 2 beside the adm3
code.

## Decision

`_group_digit()` returns the digit most of a group's columns share, and
none on a tie. The bridge rule itself is unchanged: containment both
sides and an embedding skip are still required, and naming only places
the level between them.

## Consequences

Across the 281 latest original admin1 to admin5 portolan layers, column
resolution changes for KGZ and LBN admin3 only: adm2 is its own level,
with `adm2_pcode` as its code. A group whose columns split evenly between
two digits still has none.
