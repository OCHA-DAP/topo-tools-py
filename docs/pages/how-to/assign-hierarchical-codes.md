---
title: "Assign or reconcile hierarchical codes"
---

Assign a fresh hierarchical code to a flat, uncoded layer, or reconcile
an already-coded layer against a new uncoded candidate.

Cold-starting a code on a layer with no existing convention, `code-refactor`
ranks each level's units under their parent and assigns a fresh
sequential code in your own format:

    topo-tools code-refactor admin2.geojson admin2_coded.geojson \
      --root-code AFG --delimiter . --min-width 3

Reconciling an already-coded OLD layer against an uncoded NEW candidate
(a new delivery of the same boundary), `code-update` classifies every unit
(the same engine `change` uses) and retains, replaces, or retires each
code per that classification, cascading a changed parent's new code
prefix down to its unchanged/renamed descendants. Format is
auto-detected off OLD's own codes unless overridden:

    topo-tools code-update admin1_old.geojson admin1_new.geojson

Add `--link-by-code` (plus `--code-column-a`/`--code-column-b`) if both
layers share a separate stable source identifier, to link a relocated
unit that spatial overlap alone would misclassify.

See [`code-refactor` reference](../reference/code_refactor/),
[`code-update` reference](../reference/code_update/), and the shared
[`code` explanation page](../explanation/code/) for the code format and
retention policy.
