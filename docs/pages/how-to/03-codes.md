---
title: "3. Assign hierarchical codes"
---

Third step of [preparing an administrative boundary
release](administrative-boundary-release/).

    topo-tools code-refactor admin2_topo.parquet admin2_coded.parquet \
      --root-code XYZ --delimiter . --min-width 2

Every unit's code gets overwritten with a fresh, correctly nested code
ranked under its parent, formatted per `--root-code`/`--delimiter`/
`--min-width`. Review the result, particularly any unit whose rank could
plausibly tie with a neighbor.

Reconciling an already-coded prior release against a new, uncoded
candidate instead of cold-starting uses `code-update` (see its own
reference/tutorial page); that tool always writes a changelog CSV rather
than an issues file.
