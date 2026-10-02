"""Shared coverage-topology validation and repair helpers."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from topo_tools.core.constants import (
    DETACHED_MAX_ORIGINAL_SHARE,
    DETACHED_MERGE_MAX_RATIO,
    DETACHED_MIN_NECK_RATIO,
    SNAP_ESCALATION_MAX_STEPS,
    SNAP_ESCALATION_STEP,
    SNAP_TOLERANCE,
)
from topo_tools.core.duckdb_utils import bbox_columns_sql
from topo_tools.core.units import METERS_PER_DEGREE, m2_per_deg2_factor

logger = getLogger(__name__)


def check_no_erosion(
    conn: DuckDBPyConnection,
    table_before: str,
    table_after: str,
    *,
    buffer: float = SNAP_TOLERANCE,
) -> None:
    """Raise RuntimeError if any fid's table_after geometry eroded its table_before.

    SNAP_TOLERANCE-buffered, not exact ST_Covers: GEOS leaves float noise
    far below this scale on every polygon it touches, real erosion doesn't.
    """
    eroded = conn.execute(f"""--sql
        SELECT count(*) FROM "{table_before}" o
        JOIN "{table_after}" e USING (fid)
        WHERE NOT ST_Covers(ST_Buffer(e.geom, {buffer}), o.geom)
    """).fetchall()[0][0]
    if eroded > 0:
        msg = f"extension eroded the original footprint of {eroded} fid(s)"
        raise RuntimeError(msg)


def has_invalid_edges(conn: DuckDBPyConnection, table: str) -> bool:
    """Return True if `table.geom` has any overlaps or unmatched shared edges."""
    return conn.execute(f"""--sql
        SELECT ST_CoverageInvalidEdges_Agg(geom, {SNAP_TOLERANCE}) IS NOT NULL
        FROM (SELECT UNNEST(ST_Dump(geom)).geom AS geom FROM "{table}")
    """).fetchall()[0][0]


def check_invalid_edges(conn: DuckDBPyConnection, table: str) -> None:
    """Raise RuntimeError if `table.geom` has any overlaps or unmatched shared edges."""
    if has_invalid_edges(conn, table):
        error = f"INVALID_EDGES: {table}"
        logger.error(error)
        raise RuntimeError(error)


def gap_geometries_sql(table: str) -> str:
    """Build SQL for a subquery of individual fully-enclosed interior-hole geometries.

    Dumps the union into parts first: ST_NumInteriorRings returns NULL on a
    MultiPolygon, and ST_Difference needs one polygon's own exterior ring.
    """
    return f"""(
        WITH u AS (
            SELECT ST_Union_Agg(geom) AS g
            FROM (SELECT UNNEST(ST_Dump(geom)).geom AS geom FROM "{table}")
        ),
        parts AS (
            SELECT (UNNEST(ST_Dump(g))).geom AS poly FROM u WHERE g IS NOT NULL
        ),
        holes AS (
            SELECT UNNEST(ST_Dump(
                ST_Difference(ST_MakePolygon(ST_ExteriorRing(poly)), poly)
            )).geom AS geom
            FROM parts WHERE ST_NumInteriorRings(poly) > 0
        )
        SELECT geom FROM holes WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom)
    )"""


def gap_issues_sql(
    conn: DuckDBPyConnection, table: str, *, min_width: float = SNAP_TOLERANCE
) -> str:
    """Build SQL for `table.geom`'s gap-kind issue rows, in the shared issues schema.

    Standalone or as one arm of a `UNION ALL BY NAME` with other issue kinds.
    """
    m2_per_deg2 = m2_per_deg2_factor(conn, table)
    width_m = f"(ST_MaximumInscribedCircle(geom)).radius * 2 * {METERS_PER_DEGREE}"
    thinness_ratio = "4 * pi() * ST_Area(geom) / POWER(ST_Perimeter(geom), 2)"
    return f"""
        SELECT 'gap-' || row_number() OVER (ORDER BY hash(geom)) AS key, 'gap' AS kind,
               NULL::BIGINT AS unit_a, NULL::BIGINT AS unit_b,
               NULL::BIGINT AS overlay_fid, NULL::VARCHAR AS reason,
               ST_Area(geom) * {m2_per_deg2} AS area_m2, {width_m} AS max_width_m,
               {thinness_ratio} AS thinness_ratio,
               NULL::DOUBLE AS unit_a_area_change_m2,
               NULL::DOUBLE AS unit_b_area_change_m2,
               NULL::DOUBLE AS filled_area_m2, FALSE AS fixed,
               NULL::VARCHAR AS source_file, geom
        FROM {gap_geometries_sql(table)}
        WHERE (ST_MaximumInscribedCircle(geom)).radius * 2 > {min_width}
    """


def short_source_file_sql(column: str) -> str:
    """Build SQL shortening a full source path to its last two path parts."""
    backslash = chr(92)
    posix_column = f"replace({column}, '{backslash}', '/')"
    return f"array_to_string(list_slice(str_split({posix_column}, '/'), -2, -1), '/')"


def assign_issue_rows_sql(name: str, *, source_file_expr: str = "NULL::VARCHAR") -> str:
    """Build SQL for `{name}_02_assign`'s code-join issue rows, in the shared schema.

    Requires `assignment_method`/`spatial_agrees` (assign_one/assign_many
    called with match columns); `source_file_expr` needs a real column or NULL.
    """
    return f"""
        SELECT 'code-mismatch-' || a.input_fid AS key, 'code-mismatch' AS kind,
               a.input_fid AS unit_a, NULL::BIGINT AS unit_b, a.overlay_fid,
               'code join picked a different overlay feature than spatial majority'
               AS reason,
               NULL::DOUBLE AS area_m2, NULL::DOUBLE AS max_width_m,
               NULL::DOUBLE AS thinness_ratio,
               NULL::DOUBLE AS unit_a_area_change_m2,
               NULL::DOUBLE AS unit_b_area_change_m2,
               NULL::DOUBLE AS filled_area_m2, FALSE AS fixed,
               {source_file_expr} AS source_file, c.geom
        FROM "{name}_02_assign" a
        JOIN "{name}_input_01" c ON c.fid = a.input_fid
        WHERE a.assignment_method = 'code' AND a.spatial_agrees IS NOT TRUE
        UNION ALL BY NAME
        SELECT 'code-fallback-' || a.input_fid AS key, 'code-fallback' AS kind,
               a.input_fid AS unit_a, NULL::BIGINT AS unit_b, a.overlay_fid,
               'no matching code; fell back to spatial majority' AS reason,
               NULL::DOUBLE AS area_m2, NULL::DOUBLE AS max_width_m,
               NULL::DOUBLE AS thinness_ratio,
               NULL::DOUBLE AS unit_a_area_change_m2,
               NULL::DOUBLE AS unit_b_area_change_m2,
               NULL::DOUBLE AS filled_area_m2, FALSE AS fixed,
               {source_file_expr} AS source_file, c.geom
        FROM "{name}_02_assign" a
        JOIN "{name}_input_01" c ON c.fid = a.input_fid
        WHERE a.assignment_method = 'spatial_fallback'
    """


def has_gaps(
    conn: DuckDBPyConnection, table: str, *, gap_maximum_width: float = SNAP_TOLERANCE
) -> bool:
    """Return True if `table.geom` has an interior hole at or below gap_maximum_width.

    A wider hole may be a real geographic absence, not a defect;
    gap_maximum_width=0 tolerates no hole of any size.
    """
    if gap_maximum_width == 0:
        max_interior_rings = conn.execute(f"""--sql
            WITH u AS (
                SELECT ST_Union_Agg(geom) AS g
                FROM (SELECT UNNEST(ST_Dump(geom)).geom AS geom FROM "{table}")
            )
            SELECT MAX(ST_NumInteriorRings(part))
            FROM (SELECT UNNEST(ST_Dump(g)).geom AS part FROM u)
        """).fetchall()[0][0]
        return (max_interior_rings or 0) > 0

    return conn.execute(f"""--sql
        SELECT EXISTS (
            SELECT 1 FROM {gap_geometries_sql(table)} h
            WHERE (ST_MaximumInscribedCircle(h.geom)).radius * 2 <= {gap_maximum_width}
        )
    """).fetchall()[0][0]


def check_gaps(
    conn: DuckDBPyConnection, table: str, *, gap_maximum_width: float = SNAP_TOLERANCE
) -> None:
    """Raise RuntimeError if `table.geom`'s union has a qualifying interior hole."""
    if has_gaps(conn, table, gap_maximum_width=gap_maximum_width):
        error = f"GAPS: {table}"
        logger.error(error)
        raise RuntimeError(error)


def count_gaps(conn: DuckDBPyConnection, table: str, *, min_width: float = 0) -> int:
    """Count interior holes in `table.geom`'s union that are wider than min_width."""
    return conn.execute(f"""--sql
        SELECT COUNT(*) FROM {gap_geometries_sql(table)} h
        WHERE (ST_MaximumInscribedCircle(h.geom)).radius * 2 > {min_width}
    """).fetchall()[0][0]


def is_micro_sql(geom: str, width: float = SNAP_TOLERANCE) -> str:
    """Build SQL testing whether polygon `geom` is at most `width` wide.

    2*area/perimeter bounds the inscribed-circle diameter from below, so CASE
    skips the costly ST_MaximumInscribedCircle for every clearly wide part.
    """
    return (
        f"CASE WHEN ST_IsEmpty({geom}) THEN FALSE "
        f"WHEN 2 * ST_Area({geom}) <= {width} * ST_Perimeter({geom}) "
        f"THEN (ST_MaximumInscribedCircle({geom})).radius * 2 <= {width} "
        "ELSE FALSE END"
    )


def has_micro_polygons(conn: DuckDBPyConnection, table: str) -> bool:
    """Return True if any polygon part of `table.geom` is SNAP_TOLERANCE-narrow."""
    return conn.execute(f"""--sql
        SELECT EXISTS (
            SELECT 1
            FROM (SELECT UNNEST(ST_Dump(geom)).geom AS geom FROM "{table}")
            WHERE {is_micro_sql("geom")}
        )
    """).fetchall()[0][0]


def check_micro_polygons(conn: DuckDBPyConnection, table: str) -> None:
    """Raise RuntimeError if any polygon part of `table.geom` is a micro-polygon."""
    if has_micro_polygons(conn, table):
        error = f"MICRO_POLYGONS: {table}"
        logger.error(error)
        raise RuntimeError(error)


_EMPTY_ISSUES_SQL = (
    "SELECT NULL::VARCHAR AS key, NULL::VARCHAR AS kind, NULL::BIGINT AS unit_a, "
    "NULL::BIGINT AS unit_b, NULL::BIGINT AS overlay_fid, NULL::VARCHAR AS reason, "
    "NULL::DOUBLE AS area_m2, NULL::DOUBLE AS max_width_m, "
    "NULL::DOUBLE AS thinness_ratio, NULL::DOUBLE AS unit_a_area_change_m2, "
    "NULL::DOUBLE AS unit_b_area_change_m2, NULL::DOUBLE AS filled_area_m2, "
    "NULL::BOOLEAN AS fixed, NULL::VARCHAR AS source_file, NULL::GEOMETRY AS geom "
    "WHERE FALSE"
)


def merge_micro_polygons(
    conn: DuckDBPyConnection,
    table_in: str,
    table_out: str,
    *,
    issues_table: str,
) -> int:
    """Merge each micro-polygon part into its neighbour, or drop it; return the count.

    The neighbour is the non-micro part the SNAP_TOLERANCE-buffered micro part
    overlaps most (ties to lowest fid), in any row including its own.
    """
    if not has_micro_polygons(conn, table_in):
        conn.execute(f'CREATE OR REPLACE TABLE "{issues_table}" AS {_EMPTY_ISSUES_SQL}')
        if table_out != table_in:
            conn.execute(
                f'CREATE OR REPLACE TABLE "{table_out}" AS SELECT * FROM "{table_in}"'
            )
        return 0
    tol = SNAP_TOLERANCE
    columns = {r[0] for r in conn.execute(f'DESCRIBE "{table_in}"').fetchall()}
    src = "source_file" if "source_file" in columns else "NULL::VARCHAR"
    m2_per_deg2 = m2_per_deg2_factor(conn, table_in)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _micro_all AS
        SELECT row_number() OVER () AS rnid, * FROM "{table_in}"
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _micro_parts AS
        WITH parts AS (
            SELECT rnid, fid, {src} AS source_file,
                   UNNEST(ST_Dump(geom)).geom AS geom
            FROM _micro_all
        )
        SELECT row_number() OVER () AS pid, *, {is_micro_sql("geom")} AS micro,
               {bbox_columns_sql("geom")}
        FROM parts
    """)
    count = conn.execute("SELECT count(*) FROM _micro_parts WHERE micro").fetchone()[0]
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _micro_dest AS
        WITH m AS (SELECT * FROM _micro_parts WHERE micro),
        n AS (SELECT * FROM _micro_parts WHERE NOT micro),
        pairs AS (
            SELECT m.pid, n.rnid AS dest_rnid, n.fid AS dest_fid,
                   ST_Area(ST_Intersection(ST_Buffer(m.geom, {tol}), n.geom)) AS w
            FROM m JOIN n
              ON n.xmin <= m.xmax + {tol} AND n.xmax >= m.xmin - {tol}
             AND n.ymin <= m.ymax + {tol} AND n.ymax >= m.ymin - {tol}
        )
        SELECT m.pid, m.rnid, m.fid, m.source_file, m.geom, p.dest_rnid, p.dest_fid
        FROM m LEFT JOIN (
            SELECT * FROM pairs WHERE w > 0
            QUALIFY row_number() OVER (PARTITION BY pid ORDER BY w DESC, dest_fid)
                = 1
        ) p USING (pid)
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{issues_table}" AS
        SELECT 'micro-polygon-' || row_number() OVER (ORDER BY fid, hash(geom)) AS key,
               'micro-polygon' AS kind,
               fid AS unit_a, dest_fid AS unit_b, NULL::BIGINT AS overlay_fid,
               CASE WHEN dest_rnid IS NULL THEN 'dropped: touches no feature'
                    ELSE 'merged into neighbouring feature' END AS reason,
               ST_Area(geom) * {m2_per_deg2} AS area_m2,
               (ST_MaximumInscribedCircle(geom)).radius * 2 * {METERS_PER_DEGREE}
                   AS max_width_m,
               NULL::DOUBLE AS thinness_ratio,
               NULL::DOUBLE AS unit_a_area_change_m2,
               NULL::DOUBLE AS unit_b_area_change_m2,
               NULL::DOUBLE AS filled_area_m2, TRUE AS fixed, source_file, geom
        FROM _micro_dest ORDER BY fid, hash(geom)
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{table_out}" AS
        WITH touched AS (
            SELECT rnid FROM _micro_dest
            UNION SELECT dest_rnid FROM _micro_dest WHERE dest_rnid IS NOT NULL
        ),
        pieces AS (
            SELECT p.rnid, p.geom FROM _micro_parts p SEMI JOIN touched USING (rnid)
            WHERE NOT p.micro
            UNION ALL
            SELECT dest_rnid, geom FROM _micro_dest WHERE dest_rnid IS NOT NULL
        ),
        rebuilt AS (
            SELECT rnid, ST_Union_Agg(geom) AS geom FROM pieces GROUP BY rnid
        )
        SELECT t.* EXCLUDE (geom, rnid), COALESCE(r.geom, t.geom) AS geom
        FROM _micro_all t
        LEFT JOIN rebuilt r USING (rnid)
        WHERE r.rnid IS NOT NULL OR t.rnid NOT IN (SELECT rnid FROM touched)
        ORDER BY t.rnid
    """)
    for tmp in ("_micro_all", "_micro_parts", "_micro_dest"):
        conn.execute(f"DROP TABLE IF EXISTS {tmp}")
    if count:
        logger.info("merged or dropped %d micro-polygon part(s) in %s", count, table_in)
    return count


def merge_detached_parts(  # noqa: PLR0913 (each param is a distinct required input)
    conn: DuckDBPyConnection,
    table_in: str,
    table_out: str,
    *,
    pre_clip_table: str,
    overlay_source: str,
    original_table: str | None,
    issues_table: str,
) -> int:
    """Merge small clip-detached pieces the original layer shows as clip artefacts.

    Without original_table every detached piece is reported, never merged.
    """
    multi = conn.execute(
        f'SELECT count(*) FROM "{table_in}" WHERE ST_NumGeometries(geom) > 1'
    ).fetchone()[0]
    if not multi:
        conn.execute(f'CREATE OR REPLACE TABLE "{issues_table}" AS {_EMPTY_ISSUES_SQL}')
        if table_out != table_in:
            conn.execute(
                f'CREATE OR REPLACE TABLE "{table_out}" AS SELECT * FROM "{table_in}"'
            )
        return 0
    tol = SNAP_TOLERANCE
    columns = {r[0] for r in conn.execute(f'DESCRIBE "{table_in}"').fetchall()}
    src = "a.source_file" if "source_file" in columns else "NULL::VARCHAR"
    m2_per_deg2 = m2_per_deg2_factor(conn, table_in)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _det_all AS
        SELECT row_number() OVER () AS rnid, * FROM "{table_in}"
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _det_parts AS
        WITH parts AS (
            SELECT a.rnid, a.fid, {src} AS source_file,
                   ST_NumGeometries(a.geom) > 1 AS multi,
                   UNNEST(ST_Dump(a.geom)).geom AS geom
            FROM _det_all a
        )
        SELECT row_number() OVER () AS pid, parts.*, c.overlay_fid,
               ST_Area(parts.geom) AS area, {bbox_columns_sql("parts.geom")}
        FROM parts LEFT JOIN "{pre_clip_table}" c USING (fid)
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _det_pre AS
        WITH q AS (
            SELECT fid, UNNEST(ST_Dump(geom)).geom AS geom FROM "{pre_clip_table}"
            WHERE fid IN (SELECT fid FROM _det_parts WHERE multi)
        )
        SELECT row_number() OVER () AS qid, fid, geom, ST_Area(geom) AS qarea,
               {bbox_columns_sql("geom")}
        FROM q
    """)
    # Each output piece lies inside exactly one pre-clip part, so a point test
    # finds it without building any intersection geometry.
    conn.execute("""--sql
        CREATE OR REPLACE TABLE _det_pts AS
        SELECT pid, fid, pt, ST_X(pt) AS px, ST_Y(pt) AS py
        FROM (SELECT pid, fid, ST_PointOnSurface(geom) AS pt
              FROM _det_parts WHERE multi)
    """)
    conn.execute("""--sql
        CREATE OR REPLACE TABLE _det_q AS
        SELECT p.pid, p.fid, COALESCE(q.qid, -p.pid) AS qid
        FROM _det_pts p LEFT JOIN _det_pre q
          ON q.fid = p.fid AND q.xmin <= p.px AND q.xmax >= p.px
         AND q.ymin <= p.py AND q.ymax >= p.py AND ST_Intersects(q.geom, p.pt)
        QUALIFY row_number() OVER (
            PARTITION BY p.pid ORDER BY q.qarea DESC NULLS LAST, q.qid
        ) = 1
    """)
    if original_table is None:
        conn.execute("""--sql
            CREATE OR REPLACE TABLE _det_group AS SELECT *, TRUE AS on_src FROM _det_q
        """)
    else:
        conn.execute("""--sql
            CREATE OR REPLACE TABLE _det_split AS
            SELECT pid, p.fid, p.geom, p.xmin, p.xmax, p.ymin, p.ymax
            FROM _det_parts p JOIN _det_q q USING (pid)
            WHERE q.qid IN (SELECT qid FROM _det_q GROUP BY qid HAVING count(*) > 1)
        """)
        _load_owned_original(conn, original_table, "_det_split")
        conn.execute("""--sql
            CREATE OR REPLACE TABLE _det_probe AS
            SELECT pid, s.fid, t.pt AS geom, t.px AS xmin, t.px AS xmax,
                   t.py AS ymin, t.py AS ymax
            FROM _det_split s JOIN _det_pts t USING (pid)
        """)
        _owned_original_parts(conn, "_det_probe", "_det_onsrc", pids_only=True)
        # An interior point can land in a hole of a piece mostly on the source.
        conn.execute("""--sql
            CREATE OR REPLACE TABLE _det_probe AS
            SELECT * FROM _det_split WHERE pid NOT IN (SELECT pid FROM _det_onsrc)
        """)
        _owned_original_parts(conn, "_det_probe", "_det_offsrc")
        conn.execute(f"""--sql
            CREATE OR REPLACE TABLE _det_group AS
            WITH shared AS (
                SELECT o.pid FROM _det_offsrc o JOIN _det_parts p USING (pid)
                GROUP BY o.pid, p.area
                HAVING sum(ST_Area(ST_CollectionExtract(
                    ST_Intersection(p.geom, o.geom), 3
                ))) >= {DETACHED_MAX_ORIGINAL_SHARE} * p.area
            )
            SELECT q.*, q.pid IN (SELECT pid FROM _det_onsrc)
                        OR q.pid IN (SELECT pid FROM shared) AS on_src
            FROM _det_q q
        """)
    # Per pre-clip part, the largest piece on the source footprint is kept, so an
    # extension-only piece never outranks a unit's real footprint.
    conn.execute("""--sql
        CREATE OR REPLACE TABLE _det_rank AS
        WITH flagged AS (
            SELECT g.*, p.area,
                   row_number() OVER (
                       PARTITION BY g.fid, g.qid
                       ORDER BY g.on_src DESC, p.area DESC, g.pid
                   ) = 1 AS kept
            FROM _det_group g JOIN _det_parts p USING (pid)
        )
        SELECT pid, area, kept,
               max(area) FILTER (WHERE kept) OVER (PARTITION BY fid, qid) AS kept_area
        FROM flagged
    """)
    # A point contact measures about 2*tol of neighbour boundary; an edge far more.
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _det_dest AS
        WITH d AS (
            SELECT p.*, r.area / NULLIF(r.kept_area, 0) AS ratio,
                   r.area / NULLIF(r.kept_area, 0) < {DETACHED_MERGE_MAX_RATIO} AS small
            FROM _det_rank r JOIN _det_parts p USING (pid)
            WHERE NOT r.kept
        ),
        n AS (
            SELECT * FROM _det_parts
            WHERE pid NOT IN (SELECT pid FROM d WHERE small IS NOT FALSE)
        ),
        pairs AS (
            SELECT s.pid, n.pid AS dest_pid, n.rnid AS dest_rnid, n.fid AS dest_fid,
                   ST_Length(ST_Intersection(
                       ST_Boundary(n.geom), ST_Buffer(s.geom, {tol})
                   )) AS contact
            FROM d s JOIN n
              ON n.rnid <> s.rnid
             AND n.overlay_fid IS NOT DISTINCT FROM s.overlay_fid
             AND n.xmin <= s.xmax + {tol} AND n.xmax >= s.xmin - {tol}
             AND n.ymin <= s.ymax + {tol} AND n.ymax >= s.ymin - {tol}
        ),
        best AS (
            SELECT * FROM pairs WHERE contact > {10 * tol}
            QUALIFY row_number() OVER (PARTITION BY pid ORDER BY contact DESC, dest_fid)
                = 1
        )
        SELECT d.pid, d.rnid, d.fid, d.overlay_fid, d.source_file, d.area, d.geom,
               b.dest_rnid, b.dest_fid,
               CASE WHEN b.dest_pid IS NULL THEN 'isolated'
                    WHEN d.small IS NOT TRUE THEN 'too-large'
                    WHEN ST_NumGeometries(ST_Union(d.geom, np.geom)) = 1
                        THEN 'candidate'
                    ELSE 'unattached' END AS outcome
        FROM d LEFT JOIN best b USING (pid)
        LEFT JOIN _det_parts np ON np.pid = b.dest_pid
    """)
    if original_table is None:
        conn.execute("""--sql
            UPDATE _det_dest SET outcome = 'no-original' WHERE outcome = 'candidate'
        """)
    else:
        _classify_detached_candidates(conn, overlay_source)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{issues_table}" AS
        SELECT 'detached-part-' || fid || '-'
                   || row_number() OVER (PARTITION BY fid ORDER BY pid) AS key,
               'detached-part' AS kind,
               fid AS unit_a, dest_fid AS unit_b, overlay_fid::BIGINT AS overlay_fid,
               CASE outcome WHEN 'merged' THEN 'merged into neighbouring feature'
                            WHEN 'too-large' THEN 'kept: too large to merge'
                            WHEN 'no-original' THEN 'kept: no original layer'
                            WHEN 'lobe' THEN 'kept: matches original shape'
                            ELSE 'kept: merge did not attach' END AS reason,
               area * {m2_per_deg2} AS area_m2,
               (ST_MaximumInscribedCircle(geom)).radius * 2 * {METERS_PER_DEGREE}
                   AS max_width_m,
               4 * pi() * ST_Area(geom) / POWER(ST_Perimeter(geom), 2)
                   AS thinness_ratio,
               NULL::DOUBLE AS unit_a_area_change_m2,
               NULL::DOUBLE AS unit_b_area_change_m2,
               NULL::DOUBLE AS filled_area_m2, outcome = 'merged' AS fixed,
               source_file, geom
        FROM _det_dest WHERE outcome <> 'isolated' ORDER BY pid
    """)
    count = conn.execute(
        "SELECT count(*) FROM _det_dest WHERE outcome = 'merged'"
    ).fetchone()[0]
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{table_out}" AS
        WITH moved AS (SELECT * FROM _det_dest WHERE outcome = 'merged'),
        touched AS (SELECT rnid FROM moved UNION SELECT dest_rnid FROM moved),
        pieces AS (
            SELECT p.rnid, p.geom FROM _det_parts p SEMI JOIN touched USING (rnid)
            WHERE p.pid NOT IN (SELECT pid FROM moved)
            UNION ALL
            SELECT dest_rnid, geom FROM moved
        ),
        rebuilt AS (
            SELECT rnid, ST_Multi(ST_Union_Agg(geom)) AS geom
            FROM pieces GROUP BY rnid
        )
        SELECT t.* EXCLUDE (rnid) REPLACE (COALESCE(r.geom, t.geom) AS geom)
        FROM _det_all t LEFT JOIN rebuilt r USING (rnid)
        ORDER BY t.rnid
    """)
    for tmp in (
        "_det_all",
        "_det_parts",
        "_det_pre",
        "_det_pts",
        "_det_q",
        "_det_probe",
        "_det_onsrc",
        "_det_offsrc",
        "_det_split",
        "_det_oparts",
        "_det_group",
        "_det_rank",
        "_det_dest",
    ):
        conn.execute(f"DROP TABLE IF EXISTS {tmp}")
    if count:
        logger.info("merged %d clip-detached piece(s) in %s", count, table_in)
    return count


def _load_owned_original(
    conn: DuckDBPyConnection, original_table: str, probe_table: str
) -> None:
    """Write _det_oparts: raw original parts near a probe, with their owning fid.

    Ownership is by interior point, so no key column is shared with the input.
    """
    tol = SNAP_TOLERANCE
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _det_obox AS
        SELECT {bbox_columns_sql("geom")} FROM "{original_table}"
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _det_ohit AS
        SELECT DISTINCT o.xmin, o.xmax, o.ymin, o.ymax
        FROM _det_obox o JOIN "{probe_table}" p
          ON p.xmin - {tol} <= o.xmax AND p.xmax + {tol} >= o.xmin
         AND p.ymin - {tol} <= o.ymax AND p.ymax + {tol} >= o.ymin
    """)
    # Re-reading by exact bbox streams the original and needs no stable row order.
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _det_ofeat AS
        WITH r AS (SELECT geom, {bbox_columns_sql("geom")} FROM "{original_table}")
        SELECT row_number() OVER () AS oid, r.geom
        FROM r SEMI JOIN _det_ohit h USING (xmin, xmax, ymin, ymax)
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _det_oparts AS
        WITH owner AS (
            SELECT f.oid, q.fid FROM (
                SELECT oid, pos, ST_X(pos) AS px, ST_Y(pos) AS py
                FROM (SELECT oid, ST_PointOnSurface(geom) AS pos FROM _det_ofeat)
            ) f JOIN _det_pre q
              ON q.xmin <= f.px AND q.xmax >= f.px
             AND q.ymin <= f.py AND q.ymax >= f.py AND ST_Intersects(q.geom, f.pos)
            QUALIFY row_number() OVER (PARTITION BY f.oid ORDER BY q.qid) = 1
        ),
        parts AS (
            SELECT o.fid, UNNEST(ST_Dump(f.geom)).geom AS geom
            FROM _det_ofeat f JOIN owner o USING (oid)
        )
        SELECT *, {bbox_columns_sql("geom")} FROM parts
    """)
    for tmp in ("_det_obox", "_det_ohit", "_det_ofeat"):
        conn.execute(f"DROP TABLE IF EXISTS {tmp}")


def _owned_original_parts(
    conn: DuckDBPyConnection,
    probe_table: str,
    out_table: str,
    *,
    pids_only: bool = False,
) -> None:
    """Write (pid, geom) for each owned original part touching a probe, validated."""
    select = "DISTINCT p.pid" if pids_only else "p.pid, ST_MakeValid(pp.geom) AS geom"
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{out_table}" AS
        SELECT {select}
        FROM "{probe_table}" p JOIN _det_oparts pp
          ON pp.fid = p.fid AND p.xmin <= pp.xmax AND p.xmax >= pp.xmin
         AND p.ymin <= pp.ymax AND p.ymax >= pp.ymin
        WHERE ST_Intersects(pp.geom, p.geom)
    """)


def _classify_detached_candidates(
    conn: DuckDBPyConnection, overlay_source: str
) -> None:
    """Mark each merge candidate in _det_dest as 'merged' or 'lobe'."""
    tol = SNAP_TOLERANCE
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _det_probe AS
        SELECT pid, fid, geom, {bbox_columns_sql("geom")}
        FROM (SELECT pid, fid, ST_Buffer(geom, {tol}) AS geom FROM _det_dest
              WHERE outcome = 'candidate')
    """)
    _owned_original_parts(conn, "_det_probe", "_det_src")
    # Original land the overlay clipped away beside a piece (the "neck") is
    # large when the clip sliced across the unit, near zero for a drawn lobe.
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _det_rule AS
        WITH c AS (
            SELECT pid, fid, overlay_fid, area, geom FROM _det_dest
            WHERE outcome = 'candidate'
        ),
        su AS (
            SELECT pid, ST_Union_Agg(geom) AS geom FROM _det_src GROUP BY pid
        ),
        outside AS (
            SELECT c.pid, UNNEST(ST_Dump(ST_Difference(
                su.geom, ST_CollectionExtract(ST_Intersection(ov.geom, ST_MakeEnvelope(
                    ST_XMin(su.geom) - 0.01, ST_YMin(su.geom) - 0.01,
                    ST_XMax(su.geom) + 0.01, ST_YMax(su.geom) + 0.01
                )), 3)
            ))).geom AS geom
            FROM c JOIN su USING (pid) JOIN {overlay_source} ov
              ON ov.fid = c.overlay_fid
        ),
        neck AS (
            SELECT c.pid, sum(ST_Area(o.geom)) AS neck_area
            FROM c JOIN outside o USING (pid)
            WHERE ST_Dimension(o.geom) = 2
              AND ST_Intersects(o.geom, ST_Buffer(c.geom, {tol}))
            GROUP BY c.pid
        )
        SELECT c.pid,
               COALESCE(ST_Area(ST_CollectionExtract(
                   ST_Intersection(c.geom, su.geom), 3
               )), 0) / c.area AS share,
               COALESCE(n.neck_area, 0) / c.area AS neck
        FROM c LEFT JOIN su USING (pid) LEFT JOIN neck n USING (pid)
    """)
    conn.execute(f"""--sql
        UPDATE _det_dest d SET outcome = CASE
            WHEN r.share < {DETACHED_MAX_ORIGINAL_SHARE}
              OR r.neck >= {DETACHED_MIN_NECK_RATIO} THEN 'merged'
            ELSE 'lobe' END
        FROM _det_rule r WHERE r.pid = d.pid
    """)
    for tmp in ("_det_rule", "_det_probe", "_det_src"):
        conn.execute(f"DROP TABLE IF EXISTS {tmp}")


def micro_issues_sql(
    conn: DuckDBPyConnection, table: str, *, source_file_expr: str = "source_file"
) -> str | None:
    """Return a SELECT over `{table}_micro`'s merge rows, or None if absent."""
    exists = conn.execute(
        "SELECT count(*) FROM duckdb_tables() WHERE table_name = ?", [f"{table}_micro"]
    ).fetchone()[0]
    if not exists:
        return None
    return f'SELECT * REPLACE ({source_file_expr} AS source_file) FROM "{table}_micro"'


def has_valid_topology(
    conn: DuckDBPyConnection, table: str, *, gap_maximum_width: float = SNAP_TOLERANCE
) -> bool:
    """Return True if `table.geom` has no overlap, edge mismatch, gap or micro part."""
    return (
        not has_invalid_edges(conn, table)
        and not has_gaps(conn, table, gap_maximum_width=gap_maximum_width)
        and not has_micro_polygons(conn, table)
    )


def check_valid_topology(
    conn: DuckDBPyConnection, table: str, *, gap_maximum_width: float = SNAP_TOLERANCE
) -> None:
    """Raise RuntimeError on any overlap, edge mismatch, gap or micro-polygon."""
    check_invalid_edges(conn, table)
    check_gaps(conn, table, gap_maximum_width=gap_maximum_width)
    check_micro_polygons(conn, table)


def coverage_clean(  # noqa: PLR0913 (each param is a distinct required input, not decomposable)
    conn: DuckDBPyConnection,
    table_in: str,
    table_out: str,
    *,
    fids: list[int] | None,
    gap_maximum_width: float | None = SNAP_TOLERANCE,
    snapping_distance: float | None = SNAP_TOLERANCE,
    micro_issues_table: str | None = None,
) -> None:
    """Write table_out from table_in with ST_CoverageClean applied to a subset (or all).

    Micro-polygons are merged first: ST_CoverageClean returns an all-micro row
    EMPTY. Rows map back via a synthetic rnid, since fid may repeat across sources.
    """
    issues = micro_issues_table or "_clean_micro"
    source = "_clean_in" if has_micro_polygons(conn, table_in) else table_in
    if source == table_in:
        conn.execute(f'CREATE OR REPLACE TABLE "{issues}" AS {_EMPTY_ISSUES_SQL}')
    else:
        merge_micro_polygons(conn, table_in, source, issues_table=issues)
    where = "" if fids is None else f"WHERE fid IN ({','.join(str(f) for f in fids)})"
    snap_arg = -1 if snapping_distance is None else snapping_distance
    gap_arg = -1 if gap_maximum_width is None else gap_maximum_width
    cc = f"ST_CoverageClean(list(geom ORDER BY rn), {snap_arg}, {gap_arg})"
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE _clean_all AS
        -- ST_CoverageClean's result depends on input order, so fix it by content.
        SELECT row_number() OVER (ORDER BY hash(s.geom), hash(s)) AS rnid, *
        FROM "{source}" AS s
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{table_out}" AS
        WITH sel AS (
            SELECT rnid, geom, row_number() OVER (ORDER BY rnid) AS rn
            FROM _clean_all {where}
        ),
        coll AS (
            SELECT {cc} AS g FROM sel
        ),
        dumped AS (
            SELECT (d).path[1] AS rn, (d).geom AS sub
            FROM (SELECT UNNEST(ST_Dump(g)) AS d FROM coll)
        ),
        grouped AS (
            SELECT rn, list(sub) AS subs FROM dumped GROUP BY rn
        ),
        parts AS (
            SELECT rn,
                   CASE WHEN len(subs) = 1 THEN subs[1] ELSE ST_Collect(subs) END
                       AS cleaned_geom
            FROM grouped
        ),
        mapping AS (
            SELECT sel.rnid, parts.cleaned_geom
            FROM sel JOIN parts USING (rn)
        )
        SELECT t.* EXCLUDE (geom, rnid),
               COALESCE(m.cleaned_geom, t.geom) AS geom
        FROM _clean_all t
        LEFT JOIN mapping m USING (rnid)
    """)
    for tmp in ("_clean_all", "_clean_in", "_clean_micro"):
        if tmp != micro_issues_table:
            conn.execute(f"DROP TABLE IF EXISTS {tmp}")


def coverage_clean_escalating(  # noqa: PLR0913 (mirrors coverage_clean's own inputs)
    conn: DuckDBPyConnection,
    table_in: str,
    table_out: str,
    *,
    fids: list[int] | None,
    gap_maximum_width: float | None = SNAP_TOLERANCE,
    micro_issues_table: str | None = None,
) -> None:
    """Coverage-clean, widening snapping_distance only as far as needed."""
    snap = SNAP_TOLERANCE
    for step in range(SNAP_ESCALATION_MAX_STEPS + 1):
        coverage_clean(
            conn,
            table_in,
            table_out,
            fids=fids,
            gap_maximum_width=gap_maximum_width,
            snapping_distance=snap,
            micro_issues_table=micro_issues_table,
        )
        if not has_invalid_edges(conn, table_out):
            if step:
                logger.info(
                    "coverage-clean: resolved invalid edges by escalating "
                    "snapping_distance to %s (step %d) on %s",
                    snap,
                    step,
                    table_out,
                )
            return
        snap += SNAP_ESCALATION_STEP
