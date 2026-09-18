---
title: "Compare an old and new boundary version"
---

Classify every unit between two versions of a polygon layer (unchanged,
renamed, modified, relocated, split, merge, complex, created, removed)
and get a changelog plus a colored spatial overlay for review.

    topo-tools change old.gpkg new.gpkg changelog.csv --overlay-file overlay.gpkg

By default, units are linked by spatial overlap alone. If both versions
share a stable unique code, link by it too for more reliable matching on
heavily redrawn boundaries:

    topo-tools change old.gpkg new.gpkg --link-by-code \
      --code-column-a adm2_pcode --code-column-b adm2_pcode

If legitimate boundary redraws are being misclassified as `split`/`merge`
instead of `modified`, loosen the "related" overlap threshold:

    topo-tools change old.parquet new.parquet --tau-match 0.6

See [`change` reference](../reference/change/) and its explanation page
for the full classification rules.
