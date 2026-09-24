# 0112: Numbered siblings are `_`-separated after a trailing digit

## Status

Accepted.

## Context

A second same-level column (from `schema-map`) or a parent's differing value
(from `schema-join`) is named by appending an integer: `adm2_name1`. Under a
template ending in `{n}`, such as GADM's `GID_{n}`/`NAME_{n}`, that sibling
of `GID_2` is `GID_21`, which reads as level 21 and becomes the deepest level
and row sort key (#79). Rejecting templates ending in `{n}` would remove the
ambiguity but also refuse GADM data in every tool, although GADM itself has
no numbered siblings.

## Decision

A numbered sibling is `_`-separated when its column ends in a digit
(`GID_2_1`), and appended directly otherwise (`adm2_name1`), via one shared
`sibling_name()` in `core.admin_columns`. Template families are built by one
shared `template_families()` there too, covering both the name and the code
template's prefix.

## Consequences

Templates ending in `{n}` work in every tool. Sibling names depend on the
column's last character, not the template. A raw source column named like
`GID_21` still reads as level 21, as it would without siblings.
