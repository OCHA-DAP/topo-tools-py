---
status: draft
title: "4. Codes"
---

Fourth step of COD-AB
cleaning. Reconcile the edge-matched
output of [step 3](03-edge-matching/) against the previous release, so
every unit that carries over keeps its existing code:

    topo-tools code-update admin2_previous.parquet admin2_matched.parquet \
      admin2_coded.parquet

The code format is auto-detected from the previous release's own codes.
Review the changelog CSV it writes: every `split`, `merge`, `created`,
or `removed` unit gets a new or retired code.

A country with no previous release cold-starts its codes instead:

    topo-tools code-refactor admin2_matched.parquet admin2_coded.parquet \
      --root-code XYZ --delimiter . --min-width 2

Every unit gets a fresh, correctly nested code ranked under its parent.
Review the result, particularly any unit whose rank could plausibly tie
with a neighbor.
