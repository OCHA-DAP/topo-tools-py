# 0138: `schema-join` places added columns within their own level

## Status

Accepted. Supersedes ADR-0119's placement of columns absent from the input
layer.

## Context

ADR-0119 put every column absent from the input layer after all input
columns. An input layer already holding part of a level, such as
`adm1_code` from its own crosswalk, then got that level's names after its
code (`adm1_code, adm1_name, adm1_name1`), against names before codes.

## Decision

Input columns keep input order, and a numbered sibling follows its own
family. Every other added column goes into its own level: a name after the
level's last name column or else before its first code column, a code after
the level's last code column or else the level's last column. A level
absent from the input goes before the first coarser input level, or after
all input columns when there is none.

## Consequences

Crosswalk order holds through `schema-join`, and each level's columns stay
together, names before codes. A non-admin input column between levels stays
where the input put it.
