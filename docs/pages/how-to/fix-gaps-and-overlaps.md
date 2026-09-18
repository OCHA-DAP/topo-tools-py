---
title: "Fix gaps and overlaps in one layer"
---

Detect coverage defects (gaps, overlaps) in a single polygon layer, then
fix them.

Inspect first, without fixing anything:

    topo-tools topo-detect admin2.geojson

This writes `admin2_issues.geojson`, listing every gap/overlap with its
area, width, and (for gaps) a compactness score. Review it to judge which
gaps are real features (a strait, a lake) versus digitization slivers,
before picking a fix width.

Fix gaps at or below the default snap tolerance, plus every overlap:

    topo-tools topo-clean admin2.geojson admin2_cleaned.geojson \
      --issues-file admin2_cleaned_issues.geojson

Widen the fill to every thin, elongated gap regardless of size
(`--maximum-gap-width thin`), or every detected gap regardless of shape
(`--maximum-gap-width all`), or a specific decimal-degree width. The
issues file records each defect's actual fixed outcome, not just what was
detected.

See [`topo-detect` reference](../reference/topo_detect/),
[`topo-clean` reference](../reference/topo_clean/), and their explanation
pages for the full gap/overlap detection and fix rules.
