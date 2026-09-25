---
status: draft
title: "Code"
---

Assign a fresh hierarchical code to a flat, uncoded layer, then reconcile
it against a new delivery of the same boundary.

## Assign a fresh code

`code-refactor` ranks each level's units under their parent and assigns
a fresh sequential code in your own format:

    topo-tools code-refactor admin2.geojson admin2_coded.geojson \
      --root-code AFG --delimiter . --min-width 3

## Reconcile against a new delivery

`code-update` classifies every unit of an uncoded NEW layer against the
already-coded OLD one (the same engine `change` uses), then retains,
replaces, or retires each code per that classification, cascading a
changed parent's new code prefix down to its unchanged/renamed
descendants. Format is auto-detected off OLD's own codes:

    topo-tools code-update admin2_coded.geojson admin2_new.geojson

Add `--link-by-code` (plus `--code-column-a`/`--code-column-b`) if both
layers share a separate stable source identifier, to link a relocated
unit that spatial overlap alone would misclassify.

See the [`code-refactor`](../reference/code_refactor/) and
[`code-update`](../reference/code_update/) references, and the
[`code` explanation](../explanation/code/), for the code format and
retention policy.
