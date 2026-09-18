---
title: "Reference"
---

Plain-English, verifiable reference material for each tool, using RFC 2119
keywords:

- **MUST** / **MUST NOT**: required; a violation is a bug.
- **SHOULD** / **SHOULD NOT**: expected default behavior.
- **MAY**: explicitly allowed, not required.

`docs/reference/` states *what* each tool currently does, verified directly
against source. Tests enforce a subset of these contracts; reference docs
are not a substitute for tests, and a code change must keep both in sync.

A rule identical across more than one tool goes in `shared`, referenced by
name instead of repeated in each tool's page.

<div class="grid cards" markdown>

-   :material-compare:{ .lg .middle } **change**

    ---

    Compare an old/new polygon layer pair and classify every unit.

    [:octicons-arrow-right-24: change](change)

-   :material-tag-multiple-outline:{ .lg .middle } **Code**

    ---

    code-refactor, code-update: assign or reconcile hierarchical codes.

    [:octicons-arrow-right-24: Code](code_refactor)

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

-   :material-table-edit:{ .lg .middle } **Schema**

    ---

    schema-crosswalk, schema-fill, schema-map, schema-refactor: crosswalk
    and fill a column schema.

    [:octicons-arrow-right-24: Schema](schema_crosswalk)

-   :material-share-variant-outline:{ .lg .middle } **shared**

    ---

    Common settings and gates shared across every tool.

    [:octicons-arrow-right-24: shared](shared)

-   :material-vector-polygon:{ .lg .middle } **Topo**

    ---

    topo-clean, topo-detect: detect and fix single-layer coverage defects.

    [:octicons-arrow-right-24: Topo](topo_clean)

</div>
