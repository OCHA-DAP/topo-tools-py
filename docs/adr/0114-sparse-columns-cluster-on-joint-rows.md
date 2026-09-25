# 0114: Sparse columns cluster on joint rows

## Status

Accepted.

## Context

`schema-map` clusters same-count columns into levels by pairwise
bijection. A column with any NULL (a woreda code on woreda rows only, an
adminpoints hierarchy, a capitals-only name) can't pass a bijection
against a fully-populated column, so sparse pairs were compared only when
their column names shared a digit. That used column names as positive
evidence, which 0113 rules out. It also mapped levels wrong: ETH woredas
held their level only while unrelated `Lat`/`Long` columns tipped a
tiebreak, and sparse levels without a shared digit split off or merged
into a neighbor.

## Decision

Fully-populated columns keep the bijection test. A column with any NULL
is compared only on the rows where both columns are populated, never by
name. Sparse columns populated on identical rows group first, as one
level's code and name. A group missing from a few rows attaches to the
one dense level it nests into both ways. Otherwise a group or lone column
joins the one cluster it corresponds 1:1 with on its joint rows, over at
least 10 joint values or over every value of both columns (and at least
2). One duplicated pair is tolerated; a value that collapses more than
two partners (a placeholder) is not. Anything matching more than one
cluster joins none.

A float or decimal column holding any non-whole value is excluded from
levels and bracketing, like a date/time column.

## Consequences

Checked on 757 portolan and raw-schema files and 267 CODs original
layers. Portolan `adm{k}_name`/`pcode` columns mapped to their own level
rise from 1629 to 1685 of 1816 (adminpoints 431 to 485 of 569), with no
file worse. ETH woredas, PNG and Senegal adminpoints, Afghanistan
capitals, Venezuela adminpoints, Bangladesh admin3, UKR State, Burundi
and Yemen map correctly.

On a file with fewer than 10 units, a sparse name column that is NULL on
some of its code's rows stays its own group (#99). Blanks and placeholders
still count as values (#98), and `_bridged_edges` still reads the naming
digit (#100).
