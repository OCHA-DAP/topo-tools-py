---
status: draft
title: "Topo"
---

Detect gap/overlap coverage defects in a single polygon layer, review
them, then fix them.

## Detect defects

Inspect the layer first, without fixing anything:

    topo-tools topo-detect admin2.geojson

This writes `admin2_issues.geojson`, listing every gap/overlap with its
area, width, and (for gaps) a compactness score. Review it to judge which
gaps are real features (a strait, a lake) versus digitization slivers,
before picking a fix width.

## Fix defects

Fix gaps at or below the default snap tolerance, plus every overlap:

    topo-tools topo-clean admin2.geojson admin2_cleaned.geojson \
      --issues-file admin2_cleaned_issues.geojson

Widen the fill to every thin, elongated gap regardless of size
(`--maximum-gap-width thin`), or every detected gap regardless of shape
(`--maximum-gap-width all`), or a specific decimal-degree width. The
issues file records each defect's actual fixed outcome, not just what was
detected.

See the [`topo-detect`](../reference/topo_detect/) and
[`topo-clean`](../reference/topo_clean/) references for the full
detection and fix rules.
