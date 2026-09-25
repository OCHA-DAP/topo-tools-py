---
status: draft
title: "Explanation"
---

Understanding-oriented design rationale for each tool: why it works the
way it does, stage by stage, including tradeoffs and rejected
alternatives.

`docs/explanation/` states *why* each tool is built the way it is.
`docs/reference/` states *what* it currently does; `docs/adr/` records the
one-off decisions behind both.

## Draft

<div class="grid cards draft" markdown>

-   :material-gavel:{ .lg .middle } **assign**

    ---

    Assign each child to a parent, majority vote or per-child plurality.

    [:octicons-arrow-right-24: assign](assign)

-   :material-compare:{ .lg .middle } **change**

    ---

    Compare an old/new polygon layer pair and classify every unit.

    [:octicons-arrow-right-24: change](change)

-   :material-tag-multiple-outline:{ .lg .middle } **Code**

    ---

    code, code-refactor, code-update: the shared code leaf and its two
    tools.

    [:octicons-arrow-right-24: Code](code)

-   :material-swap-horizontal:{ .lg .middle } **Edge**

    ---

    edge-clip, edge-extend, edge-match, edge-mosaic, edge-stitch: fit and
    stitch boundary layers together.

    [:octicons-arrow-right-24: Edge](edge_clip)

-   :material-package-variant-closed:{ .lg .middle } **Package**

    ---

    package, package-lines, package-points, package-polygons: cartographic
    outputs for a web map.

    [:octicons-arrow-right-24: Package](package)

-   :material-speedometer:{ .lg .middle } **performance**

    ---

    Thread-scaling benchmarks and the RTREE experiment.

    [:octicons-arrow-right-24: performance](performance)

-   :material-table-edit:{ .lg .middle } **Schema**

    ---

    schema-crosswalk, schema-fill, schema-map, schema-refactor: crosswalk
    and fill a column schema.

    [:octicons-arrow-right-24: Schema](schema_crosswalk)

-   :material-vector-polygon:{ .lg .middle } **Topo**

    ---

    topo-clean, topo-detect: detect and fix single-layer coverage defects.

    [:octicons-arrow-right-24: Topo](topo_clean)

-   :material-shape-outline:{ .lg .middle } **topology**

    ---

    The SPATIAL_JOIN memory bug and other topology-cleaning notes.

    [:octicons-arrow-right-24: topology](topology)

-   :material-memory:{ .lg .middle } **voronoi-memory**

    ---

    Per-file resampling distance and memory ceilings for large countries.

    [:octicons-arrow-right-24: voronoi-memory](voronoi-memory)

</div>
