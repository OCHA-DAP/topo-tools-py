# package-polygons

Dissolves a polygon layer into every detected coarser admin level in a
single call, replacing `dissolve`'s single `--group-by` run. Levels are
auto-detected from a target-schema YAML (the same format `schema-map`/
`schema-fill` use), no per-level `--group-by` needed.

### Example 1: default naming

Produces `adm3_admin1.geojson`, `adm3_admin2.geojson`, one file per
detected level, from a single admin3 input:

    topo-tools package-polygons adm3.geojson --target-schema schema.yaml

### Example 2: explicit output template

`{n}` MUST appear in the output path if given, formatted per level:

    topo-tools package-polygons adm3.parquet "level_{n}.parquet" --target-schema schema.yaml

### Example 3: finest level as a plain copy

Routing every level, including the finest, through the same template
still writes the finest level (as a copy of the input), unless that
level's own computed path happens to equal the input path itself:

    topo-tools package-polygons adm3.parquet "web/{n}.parquet" --target-schema schema.yaml
