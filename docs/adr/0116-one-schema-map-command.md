# 0116: One schema-map command maps and applies crosswalks

## Status

Accepted.

## Context

`schema-map` wrote a crosswalk, `schema-refactor` applied an edited one, and
`schema-crosswalk` ran both. topo-tools-js merged its three pages into one
`/schema` tool that infers or imports a crosswalk and applies it. Keeping
three CLI commands for one job left users choosing between overlapping
tools, and made the Python and JS tools differ.

## Decision

`schema-map` is the one command. By default it maps and applies, writing
the crosswalk and the mapped layer. `--csv` applies an edited
crosswalk in row order (ADR-0115), and `--map-only` writes only the
crosswalk. The written crosswalk's path moves to `--csv-output`. An
output path ending in `.csv` raises an error, so a 0.8-style
`schema-map in.gpkg out.csv` fails instead of writing a layer to a CSV
name. `schema-refactor` and `schema-crosswalk` are removed with no
deprecation period. The name stays `schema-map`: it's a verb that matches
the `_mapped` suffix, and a bare `schema` would read as "run the whole
group", like `package`, which it isn't.

## Consequences

Scripts using `schema-refactor`, `schema-crosswalk`, or `schema-map`'s
positional crosswalk path break in 0.9.0. A default run now writes the
mapped layer too. The core packages (`core.schema_map`,
`core.schema_refactor`, `core.schema_crosswalk`) keep their names as stage
groups.
