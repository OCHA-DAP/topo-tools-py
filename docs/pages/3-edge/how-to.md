---
title: "Edge matching"
sidebar:
  order: 2
  label: "How-to"
---

Fit the topology-cleaned
output of [step 2](../2-topology/how-to.md) to the previous release's country
outline, so every release keeps the same outer edge. The outline is the
previous release's admin1 from `source.coop/hdx/cod-ab/matched/{iso3}/{vNN}/`,
dissolved into one admin0 feature:

    topo-tools edge-match admin2_topo.parquet previous_admin0.parquet \
      admin2_matched.parquet --issues-file admin2_matched_issues.parquet

`edge-match` extends each unit outward to fill any gap against the
reference boundary, clips any overhang, then cleans the shared edges
across the whole layer, keeping every attribute column. The cleaning
step can shift interior edges by a hairline, so units away from the
border may show small geometry changes too. Load the issues file (if
written) as a map layer to check for units that didn't match or clip
cleanly. Where the new source's outline
differs from the previous one, confirm the difference with the data
provider: redigitizing follows the previous outline, and only a real
boundary change moves it. For a first release, with no previous outline,
agree on one with the data provider before this step.
