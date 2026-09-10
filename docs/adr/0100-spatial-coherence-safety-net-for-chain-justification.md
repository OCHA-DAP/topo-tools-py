# 0100: Spatial coherence as a safety net for two exploitable chain-justification paths

## Status

Accepted.

## Context

`docs/adr/0099`'s structural matcher justifies a chain edge either by
direct embedding evidence or, absent that, two narrower exceptions: a
finer group chaining off a genuine file-wide constant root for free
(`in_root_prefix`), and `_embeds()`'s own tolerance for exactly one
distinct non-embedding "culprit" value. Both exceptions are needed for
real files (a genuine admin0 constant with no compound code; a missing-
value sentinel like Syria's `"No_Pcode"`), but both are also exploitable
by an audit/workflow column that happens to satisfy the same cheap
statistical test without carrying any real geographic information.

Two real cases surfaced this: Moldova's `update_by` (values `UNHCR_ADMIN`/
`UNHCR_WRITER`) falsely tolerance-embedded a `created_user` root constant
(`UNHCR_WRITER`), since only `UNHCR_ADMIN` failed the substring check.
Colombia/Ecuador/Tunisia/Greece's `update_by` chained off the root for
free (no embedding evidence needed at all), then a coincidentally-clean
`created_user` chained off `update_by`, forming a 3-column audit-only
chain that outranked the real 2-column `root -> adm1_pcode` chain purely
on path length.

A first attempt applied a spatial-coherence check (`R^2` of each
candidate column's own value groups against the file's centroid spread)
as a blanket filter on chain candidacy, mirroring the existing temporal-
column exclusion. Sweeping beyond the known-broken countries falsified
this: Belgium's Brussels-Capital Region is a small enclave surrounded by
Flanders, and Costa Rica's provinces are elongated wedges from the
central highlands to both coasts, so both score low `R^2` on their real,
correctly-partitioned `adm1_pcode` despite ample data. A blanket filter
demoted both to `supplemental`, a new regression on top of fixing the
original six.

## Decision

Spatial coherence corroborates only the two specific exploitable paths
above, never chain candidacy generally:

- A finer group's edge into the root, when justified *only* by the root
  freebie (`embeds=False`), additionally requires the finer group to be
  spatially coherent, unless the table has no `geom` column loaded at
  all (`_has_geometry_column()`).
- `_embeds()`'s one-culprit tolerance is trusted only if the child column
  is also spatially coherent, same no-geometry exemption.

A column reaching the chain through direct, tolerance-free embedding
never passes through either check, so Belgium's and Costa Rica's real
`adm1_pcode` are unaffected regardless of their own `R^2` score.
Coherence itself (`_spatially_coherent()`) is `R^2 = 1 - (pooled within-
group centroid variance) / (file-wide centroid variance)`, thresholded at
`0.7`, and returns `True` (not evidence against) below
`_MIN_ROWS_FOR_SPATIAL_COHERENCE = 10` total evaluated rows, since a
low-N variance estimate is unreliable rather than genuinely incoherent.

## Consequences

Both originally-broken mechanisms (Moldova's tolerance-embed, Colombia/
Ecuador/Tunisia/Greece's root freebie) resolve their real `adm1_pcode`
correctly. The eight countries the blanket-filter prototype broke (BEL,
CRI, FJI, GLP, GUF, LUX, SWZ, XJK) are unaffected by the narrower design,
since none of their real admin columns ever depend on the root freebie or
the tolerance exception.

Verified against the full 394-file portolan corpus (no new regressions
against the established 114-file baseline), the full UNHCR adm1 (212
countries) and adm2 (209 countries) sweeps (zero missing pcodes, zero
errors), and OCHA/UNICEF/WFP adm1-5 sweeps (zero errors/empty results).

A table with no `geom` column loaded degrades to the exact pre-existing
behavior (neither check applies), which is why `resolve_columns()`
itself stays unchanged and this only touches `_build_chain()`/`_embeds()`
internals.
