---
title: "3. Assign hierarchical codes"
---

Third step of [preparing an administrative boundary
release](administrative-boundary-release/). Continues from the cleaned
output of [step 2](02-fix-topology/).

    topo-tools code-refactor district_topo.parquet district_coded.parquet \
      --root-code TT --delimiter . --min-width 2

Every district's placeholder code gets overwritten with a fresh, correctly
nested code ranked under its province: `TT.01`/`TT.02` for the provinces,
`TT.01.01` through `TT.02.04` for the districts.

Reconciling an already-coded prior release against a new, uncoded
candidate instead of cold-starting uses `code-update` (see its own
reference/tutorial page); that tool always writes a changelog CSV rather
than an issues file.

Next: [fit a finer level into one district](04-fit-finer-level/)
(uncommon, safe to skip), or straight to [deriving ancestor
levels](05-fill-and-derive-ancestors/).
