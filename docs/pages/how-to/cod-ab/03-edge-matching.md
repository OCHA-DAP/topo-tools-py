---
status: draft
title: "3. Edge matching"
---

Third step of COD-AB
cleaning. Fit the topology-cleaned
output of [step 2](02-topology/) to a reference admin0 boundary, so the
release's outer edge follows the agreed country outline:

    topo-tools edge-match admin2_topo.parquet reference_admin0.parquet \
      admin2_matched.parquet --issues-file admin2_matched_issues.parquet

`edge-match` extends each unit outward to fill any gap against the
reference boundary, then clips any overhang, keeping every attribute
column. Load the issues file (if written) as a map layer to check for
units that didn't match or clip cleanly.
