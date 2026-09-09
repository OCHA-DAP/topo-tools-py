# package-points

Produces one label point per admin unit per detected level, combined into
a single output file, for web-map label placement. Uses the pole of
inaccessibility, not the centroid, so a label always lands on its own
territory.

### Example 1: default naming

Produces `adm3_points.geojson`, one combined file covering every detected
level:

    topo-tools package-points adm3.geojson

### Example 2: custom depth column

Rename the stamped level column from `adm_lvl` to something else:

    topo-tools package-points adm3.geojson --depth-column level
