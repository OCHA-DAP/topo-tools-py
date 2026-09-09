# Run an at-scale test against the portolan catalog

Use the portolan catalog (see `CLAUDE.md`'s Test Datasets section for its
location and the read-only hard rule) when the recommended West Africa
cluster isn't enough, e.g. checking a fix at real multi-thousand-fid
scale, or exercising `change` against a genuine old/new version pair.

## Layout

STAC-like: `{iso3}/{latest,vNN}/{adm0..adm3,lines,points}/{original,
extended,matched}.parquet`. Distinct `vNN` dirs are always genuinely
different content; `latest` is whichever `vNN` is newest.

## Picking a file (`edge-extend` / `edge-match` / `topo-clean`)

Any single `{iso3}/{vNN}/{adm_level}/original.parquet` works. Point every
`--output-path`/`--tmp-dir`/`--debug` export outside the catalog (the
session scratchpad or `/tmp`), never back into `portolan/`.

## Picking a file (`package-polygons` / `package-points` / `package-lines` / `package`)

`global/admin{0..4}/admin{0..4}.parquet` holds the full global dataset at
each level, already carrying `adm{0..4}_pcode`/`adm{0..4}_name` columns and
its own `adm_lvl` real-depth stamp; `global/admin4/admin4.parquet` (the
finest, 217,223 rows) is the right single input for any of these tools,
combining every level's rows in one file. Structural auto-detection (the
default, no `--name-field`/`--code-field` needed) finds every level
regardless of naming convention, `_pcode` included. Since the file already
has its own `adm_lvl` column, pass `--depth-column` set to something else
(e.g. `pkg_lvl`) to `package-points`/`package-lines`, or they raise
`ValueError` on the name collision rather than silently overwriting it.
`iso3` filters down to one country's rows for a smaller/faster run (e.g.
`IDN` at 81,693 rows, `PHL` at 42,019, both large enough for a real
mid-scale stress test without the full global run's cost).

## Picking a parent/clip layer (`edge-match` / `edge-mosaic`)

Use `/Users/computer/GitHub/fieldmaps/adm0-generator/outputs/adm0/osm/intl/adm0_polygons.parquet`
as the global admin0 parent/clip layer; it's outside the portolan catalog
so it's safe to pass directly as `CLIP_FILE`. Also available at
`https://data.fieldmaps.io/adm0/osm/intl/adm0_polygons.parquet` for anyone
without local repo access.

## Picking an old/new pair (`change`)

1. Browse the country's catalog (local path, or fetch `./{iso3}/catalog.json`
   from the STAC root) and list its `vNN` dirs.
2. Not every country/admin-level has 2+ versions yet, so confirm both `vNN`s
   you want to compare actually exist before running `change`.
3. Run `change` with the older version as the first argument, the newer as
   the second; point every output path outside the catalog.

`docs/explanation/change.md`'s "Portolan-scale profiling" section has real
timing/memory numbers from Philippines admin3 (`v02`->`v03`), Ethiopia
admin3 (`v01`->`v04`), and Ukraine admin3 (`v01`->`v05`) runs, plus a
`--link-by-code` footgun found on the Philippines pair.
`docs/explanation/package_polygons.md`, `docs/explanation/package_points.md`,
and `docs/explanation/package_lines.md` each have their own
"Portolan-scale profiling" section with a full global admin4 run.

## Prefer the catalog's own GeoParquet over a freshly-converted GDB export

If a global/combined export (e.g. an `.gdb.zip`) exists outside the
catalog for the same content, use the catalog's own per-country/per-level
GeoParquet instead for topology-sensitive testing. An ad hoc
`gdal vector convert` from a zipped FileGDB (OpenFileGDB driver) was found
to introduce real topology defects (`has_invalid_edges()` true) not present
in the canonical portolan GeoParquet of the same 213,503-row dataset,
likely from OGR's `organizePolygons()` part-reassembly heuristic on
many-part multipolygons; the GDB source logged `organizePolygons() received
a polygon with more than 100 parts` during conversion. Use the portolan
catalog's own GeoParquet files for topology-sensitive at-scale testing, not
a freshly-converted GDB export, even of nominally the same dataset.
