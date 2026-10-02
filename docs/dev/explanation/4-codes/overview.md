---
title: "Code"
sidebar:
  order: 7
  label: "Overview"
  badge:
    text: Draft
    variant: caution
---

Why code-create and code-update share one hierarchical-code engine
(`core.code`), and how each uses it differently.

- [code](code.md): the shared next-available-integer-per-parent leaf.
- [code-create](code_create.md): cold-starts a code with no existing
  convention.
- [code-update](code_update.md): reconciles an already-coded layer,
  retaining/replacing/retiring per unit.
