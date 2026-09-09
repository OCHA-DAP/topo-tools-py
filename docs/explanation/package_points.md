# Package-Points Explanation

`package-points` produces one label point per admin unit per detected
level, combined into a single output file, for web-map label placement.
It uses the pole of inaccessibility rather than the centroid, since a
centroid can fall outside a concave or multi-part polygon (e.g. a
crescent-shaped or archipelago admin unit), which would place a label off
its own territory.

## Usage

```sh
topo-tools package-points admin3.geojson
```

```python
from topo_tools import package_points

package_points("admin3.parquet")
```

`OUTPUT_FILE` (positional, optional) defaults to `INPUT_FILE` with a
`_points` suffix.

Run `topo-tools package-points --help` for the full, always-current option
list.

## Pipeline

1. **`_01_inputs`**: loads and reprojects the input, same as
   `package-polygons`.
2. **`_02_points`**: detects every level (explicit schema or structural
   auto-detection, same as `package-polygons`), then per level: dissolves
   via `core.dissolve`'s `_02_dissolve.main()` (grouped by that level's
   code column), checks the dissolved row count against the input's own
   distinct code-column count, computes each dissolved unit's
   `ST_MaximumInscribedCircle(geom).center` as its label point, stamps the
   depth column, and checks every point is `ST_Covers`-ed by its own
   source polygon. Every level's points table is combined via
   `UNION ALL BY NAME`, not sequential inserts into a fixed-schema table,
   since a coarser level's dissolve drops every finer-level column.
3. **`_03_outputs`**: exports the combined table directly; no topology
   gate applies, since this is a derived cartographic layer, not a
   coverage layer.

## Why `ST_MaximumInscribedCircle`, not the centroid

`ST_Centroid` is a purely geometric average of a polygon's area and can
land outside the polygon itself for a concave shape, or on a body of water
between two islands for a multi-part one. `ST_MaximumInscribedCircle`'s
`center` is always interior to the polygon (it's the center of the largest
circle that fits inside it), the standard technique web-map label
placement uses to keep a label anchored on its own territory.

## Portolan-scale profiling

The real target scale for this tool, `--debug` off, Apple Silicon/10 logical
cores:

| Run                              | Points out (all levels combined)   | Wall time | RSS peak | Result                              |
| --------------------------------- | ---------------------------------- | --------- | -------- | ------------------------------------ |
| Global admin4 (`portolan/global/admin4/admin4.parquet`, 217,223 rows, 5 detected levels, `--depth-column pkg_lvl`) | 297,503 (111 + 1,889 + 19,842 + 58,438 + 217,223) | 483s | 8.01 GB | Every point `ST_Covers`-ed by its own source polygon |

**Real-data gotcha: `depth_column` collision.** The portolan catalog's own
global admin files already carry an `adm_lvl` column of their own (the
source's real-depth stamp); `package-points`' default `depth_column`
(`"adm_lvl"`) collides with it. `_02_points.py` raises `ValueError` on this
collision (`depth_column {value!r} already exists on {table!r}`) rather
than silently producing a renamed duplicate column the way DuckDB's own
`CREATE TABLE AS SELECT` does for a repeated column name; pass a
non-colliding `--depth-column` (e.g. `pkg_lvl`, as above) against such a
file.
