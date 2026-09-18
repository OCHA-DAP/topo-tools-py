---
title: "Explanation"
---

Understanding-oriented design rationale for each tool: why it works the
way it does, stage by stage, including tradeoffs and rejected
alternatives.

`docs/explanation/` states *why* each tool is built the way it is.
`docs/reference/` states *what* it currently does; `docs/adr/` records the
one-off decisions behind both.

<div class="grid cards" markdown>

-   :material-gavel:{ .lg .middle } **assign**

    ---

    Assign each child to a parent, majority vote or per-child plurality.

    [:octicons-arrow-right-24: assign](assign)

-   :material-compare:{ .lg .middle } **change**

    ---

    Compare an old/new polygon layer pair and classify every unit.

    [:octicons-arrow-right-24: change](change)

-   :material-code-tags:{ .lg .middle } **code**

    ---

    Shared next-available-integer-per-parent leaf used by code-refactor/code-update.

    [:octicons-arrow-right-24: code](code)

-   :material-auto-fix:{ .lg .middle } **code-refactor**

    ---

    Cold-start a hierarchical code on a flat, finest-level input.

    [:octicons-arrow-right-24: code-refactor](code_refactor)

-   :material-update:{ .lg .middle } **code-update**

    ---

    Reconcile an already-coded OLD layer against an uncoded NEW candidate.

    [:octicons-arrow-right-24: code-update](code_update)

-   :material-scissors-cutting:{ .lg .middle } **edge-clip**

    ---

    Assign each child to its parent, then clip it to that parent's geometry.

    [:octicons-arrow-right-24: edge-clip](edge_clip)

-   :material-shape-polygon-plus:{ .lg .middle } **edge-extend**

    ---

    Extend polygon boundaries outward with Voronoi diagrams to fill gaps.

    [:octicons-arrow-right-24: edge-extend](edge_extend)

-   :material-puzzle-outline:{ .lg .middle } **edge-match**

    ---

    Fit a child layer into a coarser parent/clip layer.

    [:octicons-arrow-right-24: edge-match](edge_match)

-   :material-view-grid-outline:{ .lg .middle } **edge-mosaic**

    ---

    Re-clip an already-extended child layer into a new parent layer.

    [:octicons-arrow-right-24: edge-mosaic](edge_mosaic)

-   :material-needle:{ .lg .middle } **edge-stitch**

    ---

    Close seams in an already-tiled layer with one coverage-clean pass.

    [:octicons-arrow-right-24: edge-stitch](edge_stitch)

-   :material-package-variant-closed:{ .lg .middle } **package**

    ---

    Run package-polygons, package-points, and package-lines in one call.

    [:octicons-arrow-right-24: package](package)

-   :material-vector-polyline:{ .lg .middle } **package-lines**

    ---

    One deduplicated line network of admin boundaries, tagged by adjacency.

    [:octicons-arrow-right-24: package-lines](package_lines)

-   :material-dots-hexagon:{ .lg .middle } **package-points**

    ---

    One label point per admin unit, using the pole of inaccessibility.

    [:octicons-arrow-right-24: package-points](package_points)

-   :material-vector-polygon:{ .lg .middle } **package-polygons**

    ---

    Dissolve a polygon layer into every detected coarser admin level.

    [:octicons-arrow-right-24: package-polygons](package_polygons)

-   :material-speedometer:{ .lg .middle } **performance**

    ---

    Thread-scaling benchmarks and the RTREE experiment.

    [:octicons-arrow-right-24: performance](performance)

-   :material-swap-horizontal-bold:{ .lg .middle } **schema-crosswalk**

    ---

    schema-map and schema-refactor in one call.

    [:octicons-arrow-right-24: schema-crosswalk](schema_crosswalk)

-   :material-format-color-fill:{ .lg .middle } **schema-fill**

    ---

    Fill down admin columns and stamp each row's real depth.

    [:octicons-arrow-right-24: schema-fill](schema_fill)

-   :material-sitemap:{ .lg .middle } **schema-map**

    ---

    Map a source-column to target-schema crosswalk, structurally.

    [:octicons-arrow-right-24: schema-map](schema_map)

-   :material-table-edit:{ .lg .middle } **schema-refactor**

    ---

    Rename/drop columns per a crosswalk from schema-map.

    [:octicons-arrow-right-24: schema-refactor](schema_refactor)

-   :material-broom:{ .lg .middle } **topo-clean**

    ---

    Detect and fix coverage defects in a single layer.

    [:octicons-arrow-right-24: topo-clean](topo_clean)

-   :material-map-search-outline:{ .lg .middle } **topo-detect**

    ---

    Scan a polygon layer for gap/overlap coverage defects.

    [:octicons-arrow-right-24: topo-detect](topo_detect)

-   :material-shape-outline:{ .lg .middle } **topology**

    ---

    The SPATIAL_JOIN memory bug and other topology-cleaning notes.

    [:octicons-arrow-right-24: topology](topology)

-   :material-memory:{ .lg .middle } **voronoi-memory**

    ---

    Per-file resampling distance and memory ceilings for large countries.

    [:octicons-arrow-right-24: voronoi-memory](voronoi-memory)

</div>
