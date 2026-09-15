# code-refactor

Cold-starts a hierarchical code on a flat, finest-level input: no
existing code convention assumed, format fully configurable
(`--root-code`/`--delimiter`/`--min-width`, all required).

### Example 1: structural auto-detection, no code column exists yet

    topo-tools code-refactor admin2.geojson --root-code AFG --delimiter . --min-width 3

### Example 2: explicit level columns, ambiguous auto-detection

    topo-tools code-refactor admin2.geojson --root-code AFG --delimiter . --min-width 3 \
      --code-field adm{n}_code --name-field adm{n}_name

### Example 3: overflow issues report

Writes `admin2_coded.geojson` and, only if any parent exceeds `10 **
min_width - 1` children, `admin2_coded_issues.csv`:

    topo-tools code-refactor admin2.geojson admin2_coded.geojson --root-code AFG --delimiter . --min-width 3
