# 0101: `core.code` is a shared, fully generic primitive; no organization's format is hardcoded

## Status

Accepted.

## Context

`topo-tools` had no way to produce or maintain a hierarchical admin code.
The COD-AB standard (a real, external convention this repo's users need
to target) defines a specific format: dot-delimited, 3-digit zero-padded,
ISO3 root, plus a changelog-driven retention policy for maintaining it
release over release. That specific format is one target a caller can
configure, not an assumption to bake into the tool: a disputed-territory
user-assigned root (`XKO`), a different delimiter, or a different pad
width are all equally valid inputs for an organization with its own
convention.

## Decision

The cascade/format/rewrite mechanism lives in its own neutral leaf,
`topo_tools/core/code/`, alongside `core.assign`/`core.dissolve`: no
`api.*()`/CLI of its own, importable by any tool package, importing none
of them back. `CodeFormat` (`root_code`, `delimiter`, `min_width`) has no
default values on any field; `resolve_code_format()` is a thin validating
constructor, not a defaults-filling one. No COD-AB-specific literal
(`.`, `3`, `adm{n}_pcode`, an ISO3 example) appears anywhere in
`core/code/`, `core/code_refactor/`, or `core/code_update/`'s source,
including as a Python or Click default value; `code-refactor`'s
`--root-code`/`--delimiter`/`--min-width` are all required flags with no
default for this reason.

Naming follows the same principle: `code`, never `pcode`, throughout
every module/function/CLI flag/output column, so the generic mechanism
never reads as COD-AB-specific even where it happens to produce
COD-AB-shaped output. `root_code` is opaque everywhere, never shape- or
length-checked, so a disputed-territory prefix works identically to an
ISO3 one.

## Consequences

A future "profile" feature (e.g. `--profile cod-ab` loading a bundled
preset of `root_code`/`delimiter`/`min_width` plus a specific sort-column
tie-break) can supply COD-AB's specific values as external data on top of
this generic engine, without touching `core/code/` itself. Today, every
caller (COD-AB or otherwise) configures the format explicitly on
`code-refactor`, or lets `code-update` detect it from OLD's own existing
codes (`docs/explanation/code.md`).
