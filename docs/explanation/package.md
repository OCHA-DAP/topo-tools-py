# Package Explanation

`package` runs `package-polygons`, `package-points`, and `package-lines`
against one input in a single call, for the common case of wanting the
full cartographic bundle at once. It calls each sub-tool's own `api.*()`
function directly (`api.package_polygons.package_polygons()`,
`api.package_points.package_points()`, `api.package_lines.package_lines()`),
the same composition pattern `schema-crosswalk` uses on `schema-map` and
`schema-refactor`, one layer up (at the `api.*()` layer, not the stage
layer). Each sub-tool reads and reprojects the input independently, three
reads total; no attempt is made to share one connection or `_01` table
across them, since each sub-tool already manages its own.

## Usage

```sh
topo-tools package admin3.geojson
```

```python
from topo_tools import package

package("admin3.parquet")
```

Run `topo-tools package --help` for the full, always-current option list.

## Output path templating

`--output`/`output_path`, if given, MUST contain a literal `{x}`
placeholder. `{x}` is substituted per sub-call with a fixed, hardcoded
word: `admin{n}` for `package-polygons` (itself still `{n}`-templated per
level, unaffected by `package`'s own substitution), `points` for
`package-points`, `lines` for `package-lines`. `{n}` is never exposed to
`package`'s own caller directly; it only ever exists embedded inside the
`admin{n}` substitution, so it can't leak into the points/lines paths. A
caller who wants a different word for one output calls that tool directly
instead, e.g. `package-polygons` accepts any custom `{n}`-containing
template.
