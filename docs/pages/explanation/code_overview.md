---
status: draft
title: "Code"
---

Why code-refactor and code-update share one hierarchical-code engine
(`core.code`), and how each uses it differently.

- [code](code/): the shared next-available-integer-per-parent leaf.
- [code-refactor](code_refactor/): cold-starts a code with no existing
  convention.
- [code-update](code_update/): reconciles an already-coded layer,
  retaining/replacing/retiring per unit.
