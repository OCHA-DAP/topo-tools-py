---
name: cod-ab-cleaning
description: Clean and reconcile COD-AB administrative boundary polygons with topo-tools (edge-fitting, topology repair, cartographic packaging).
---

Guide the user through cleaning and reconciling a COD-AB administrative
boundary layer with topo-tools.

1. Confirm the input layer, its admin level, and its parent/clip layer (a
   coarser admin level or national boundary), if any.
2. If the layer needs fitting to that parent, run `topo-tools edge-match
   children.geojson parents.geojson`.
3. If there's no parent layer and the layer's own topology has gaps/
   overlaps, run `topo-tools topo-clean example.geojson` instead.
4. Once clean, dissolve into every coarser admin level and produce label
   points/boundary lines with `topo-tools package cleaned.geojson`.
5. For column renaming/crosswalking to a target schema first, run
   `topo-tools schema-crosswalk example.geojson`.

Reference: https://ocha-dap.github.io/topo-tools-py/reference/
Tutorials: https://ocha-dap.github.io/topo-tools-py/tutorials/
