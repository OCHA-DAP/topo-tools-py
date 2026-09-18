---
title: "How-to"
---

Task-oriented, step-by-step guides. Each one gets a specific job done,
assuming you already know the basics.

<div class="grid cards" markdown>

-   :material-map-marker-path:{ .lg .middle } **Prepare an administrative boundary release**

    ---

    Chain several tools to take a raw administrative boundary delivery
    through to a clean, coded, packaged release.

    [:octicons-arrow-right-24: Prepare a release](administrative-boundary-release/)

-   :material-vector-polygon:{ .lg .middle } **Fix gaps and overlaps in one layer**

    ---

    Detect coverage defects in a single polygon layer, then fix them.

    [:octicons-arrow-right-24: Fix gaps and overlaps](fix-gaps-and-overlaps/)

-   :material-swap-horizontal:{ .lg .middle } **Fit a finer layer to a coarser parent**

    ---

    Extend and clip a finer child layer so it fits a coarser parent/clip
    layer exactly.

    [:octicons-arrow-right-24: Fit a finer layer](fit-a-finer-layer-to-a-parent/)

-   :material-table-edit:{ .lg .middle } **Map and rename columns to a target schema**

    ---

    Crosswalk a source file's columns onto a target admin-hierarchy
    schema, then rename/drop columns to match.

    [:octicons-arrow-right-24: Map and rename columns](map-and-rename-columns/)

-   :material-stairs:{ .lg .middle } **Fill hierarchy columns down to each row's real depth**

    ---

    Stamp each row with its real admin depth, then cascade every
    admin-hierarchy column down to that depth.

    [:octicons-arrow-right-24: Fill hierarchy columns](fill-hierarchy-columns/)

-   :material-map-outline:{ .lg .middle } **Package a layer for a web map**

    ---

    Derive the cartographic outputs a web map needs from one clean
    polygon layer.

    [:octicons-arrow-right-24: Package for a web map](package-for-a-web-map/)

-   :material-compare:{ .lg .middle } **Compare an old and new boundary version**

    ---

    Classify every unit between two versions of a polygon layer and get a
    changelog plus a spatial overlay for review.

    [:octicons-arrow-right-24: Compare boundary versions](compare-boundary-versions/)

-   :material-tag-multiple-outline:{ .lg .middle } **Assign or reconcile hierarchical codes**

    ---

    Assign a fresh hierarchical code to a flat, uncoded layer, or
    reconcile an already-coded layer against a new uncoded candidate.

    [:octicons-arrow-right-24: Assign hierarchical codes](assign-hierarchical-codes/)

-   :material-content-cut:{ .lg .middle } **Clip children to a parent, or stitch tiled seams**

    ---

    Use the two lower-level primitives `edge-match`/`edge-mosaic` chain
    internally, directly, for a narrower job than a full fit.

    [:octicons-arrow-right-24: Clip and stitch tiles](clip-and-stitch-tiles/)

-   :material-arrow-expand-all:{ .lg .middle } **Extend a layer outward to fill gaps**

    ---

    Extend a polygon layer's boundaries outward using Voronoi diagrams,
    producing a complete coverage layer with no external gaps.

    [:octicons-arrow-right-24: Extend a layer outward](extend-a-layer-outward/)

</div>
