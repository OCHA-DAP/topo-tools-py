---
status: draft
title: Topology Tools
---

# Topology Tools

DuckDB-powered geospatial topology utilities for cleaning and reconciling
administrative boundary polygons, as a Python/CLI package and library.

## Boundary cleaning { .section-label }

<div class="phase-steps" markdown>

1.  **[Schema](1-schema/index.md)**

    Map source columns to admin code and name columns, then apply the crosswalk.

    :tools-schema-map:

2.  **[Topology](2-topology/index.md)**

    Find gaps and overlaps between units, then clean them.

    :tools-topo-clean:

3.  **[Edge matching](3-edge/index.md)**

    Fit units to a reference boundary so the outer edge follows the agreed outline.

    :tools-edge-match:

4.  **[Codes](4-codes/index.md)**

    Keep the previous release's codes for units that carry over, or cold-start codes when there is no previous release.

    :tools-code-update:

5.  **[Names](5-names/index.md)**

    Review names by hand: duplicates under the same parent, near-duplicate typos, blanks and placeholders, and encoding artifacts.

    :steps-names:

6.  **[Packaging](6-packaging/index.md)**

    Build per-level polygons, label points, and the boundary line network for release.

    :tools-package:

</div>

Each phase has a step-by-step guide, a tutorial, reference pages (what
each tool does) and explanation pages (why it works that way).

## Using with agents

<div class="grid cards" markdown>

-   **[Claude Code](agents/claude-code.md)**: install the plugin in VS Code
    or a terminal, then run it from Claude Code.

-   **[Other agents](agents/other-agents.md)**: paste one prompt into any
    agent that can read a URL. Nothing to install.

</div>

## Installation

The boundary cleaning steps run the `topo-tools` CLI. Install it with:

=== "uv"

    ```sh
    uv tool install topo-tools   # CLI
    uv add topo-tools            # Python library
    ```

=== "pip"

    ```sh
    pip install topo-tools       # CLI or library
    pipx install topo-tools      # CLI
    ```

=== "conda"

    ```sh
    conda install -c conda-forge topo-tools   # CLI or library
    ```

    Recommended on Windows. `mamba` and `pixi` install it from the same channel.

=== "Homebrew"

    ```sh
    brew install OCHA-DAP/topo-tools/topo-tools
    ```

    macOS/Linux, with no Python tooling required.

Inputs and outputs: GeoParquet, GeoPackage, Shapefile and GeoJSON. The
output format matches the input format.

The tools are also available as a
[web app](https://ocha-dap.github.io/topo-tools-js/), which runs DuckDB in
the browser: nothing to install, and files are processed locally.
