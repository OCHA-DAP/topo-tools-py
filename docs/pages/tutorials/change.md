---
status: draft
title: "change"
---

Classify every unit between two versions of a polygon layer (unchanged,
renamed, modified, relocated, split, merge, complex, created, removed)
and get a changelog plus a colored spatial overlay for review.

## Compare two versions

    topo-tools change old.gpkg new.gpkg changelog.csv --overlay-file overlay.gpkg

Open `overlay.gpkg` alongside `changelog.csv` to review each classified
unit on a map.

## Link by a shared code

By default, units are linked by spatial overlap alone. If both versions
share a stable unique code, link by it too for more reliable matching on
heavily redrawn boundaries:

    topo-tools change old.gpkg new.gpkg --link-by-code \
      --code-column-a adm2_pcode --code-column-b adm2_pcode

## Loosen the overlap threshold

If legitimate boundary redraws are being misclassified as `split`/`merge`
instead of `modified`, loosen the "related" overlap threshold:

    topo-tools change old.gpkg new.gpkg --tau-match 0.6

See the [`change` reference](../reference/change/) for the full
classification rules.
