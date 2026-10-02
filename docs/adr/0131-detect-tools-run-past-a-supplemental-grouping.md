# 0131: Detect tools run past a supplemental grouping

## Status

Accepted. Narrows 0121.

## Context

0121 stops the structural code tools when detection sets a column aside
as a supplemental coarser grouping, since it may be a missed level with
parent-local codes. `resolve_levels()` applied the same refusal to
`code-detect` and `name-detect`, so 14 of the 281 latest original admin1
to admin5 portolan layers got no code or name checks.

Their 26 supplemental columns are real coarser groupings (AFG regions,
AZE economic regions, BFA's previous units, CPV islands, NGA senatorial
districts, MMR admin5's `adm2_name1`) or attributes that aren't places:
unit types (VNM `adm1_type_en`, AZE `adm1_type`) and near-empty columns
(ETH `adm2_alt_name`, SLE `adm4_ref`). An attribute's groups are spread
across the map (`_spatially_coherent()` false); a level's never are.

## Decision

- `resolve_levels()` refuses only a skipped level or a layer with no level
  that has both a code and a name. A supplemental grouping stays a
  `supplemental-column` warning in `schema-detect`.
- `code-create` and `code-update` refuse only a supplemental grouping
  whose groups cluster on the map, taken as true without geometry or
  under 10 rows.

## Consequences

The detect tools are read-only, so a missed level costs at most extra
`duplicate-name` warnings, names compared under a parent one level too
coarse. Run on the 14 layers, they found real defects in MMR admin5 (22
code rows, 2 name rows) and one duplicate name in SLE admin4, and no
other rows. The code tools still refuse 11 of the 14 on a grouping,
since only VNM admin1, ETH admin2 and SLE admin4 have no coherent one.
