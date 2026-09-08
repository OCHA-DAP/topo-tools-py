"""Builds a deduplicated shared+exterior boundary line network, tagged by depth."""

from duckdb import DuckDBPyConnection

from topo_tools.core.dissolve import _02_dissolve as dissolve_stage
from topo_tools.core.duckdb_utils import bbox_columns_sql
from topo_tools.core.schema_map._target_schema import TargetSchema

_EMPTY_LINES = "ST_GeomFromText('MULTILINESTRING EMPTY')"


def _classification_sql(levels: list[int], code_columns: list[str]) -> str:
    if len(levels) == 1:
        return str(levels[0])
    cases = "".join(
        f'WHEN l."{col}" IS DISTINCT FROM r."{col}" THEN {level} '
        for level, col in zip(levels[:-1], code_columns[:-1], strict=True)
    )
    return f"CASE {cases}ELSE {levels[-1]} END"


def _check_every_fid_present(
    conn: DuckDBPyConnection, dissolved: str, lines: str
) -> None:
    missing = conn.execute(f"""--sql
        SELECT fid FROM "{dissolved}"
        WHERE fid NOT IN (
            SELECT left_fid FROM "{lines}"
            UNION
            SELECT right_fid FROM "{lines}" WHERE right_fid IS NOT NULL
        )
    """).fetchall()
    if missing:
        fids = [m[0] for m in missing]
        msg = f"{lines}: fid(s) missing from every boundary row: {fids}"
        raise ValueError(msg)


def main(
    conn: DuckDBPyConnection,
    name: str,
    levels: list[int],
    schema: TargetSchema,
    depth_column: str,
) -> None:
    """Dissolve at the finest level, then extract and classify its boundary network."""
    reserved = {"left_fid", "right_fid", "boundary_type", "geom"}
    if depth_column in reserved:
        msg = f"depth_column {depth_column!r} collides with a fixed output column"
        raise ValueError(msg)

    code_columns = [schema.code_field.format(n=n) for n in levels]
    dissolved = f"{name}_02_dissolved"
    dissolve_stage.main(
        conn,
        f"{name}_01",
        dissolved,
        group_by=[code_columns[-1]],
        target_schema=schema,
    )

    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02_parts" AS
        SELECT fid, (dump).geom AS geom, {bbox_columns_sql("(dump).geom")}
        FROM "{dissolved}", UNNEST(ST_Dump(geom)) AS d(dump)
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02_pairs" AS
        SELECT DISTINCT a.fid AS left_fid, b.fid AS right_fid
        FROM "{name}_02_parts" a JOIN "{name}_02_parts" b
          ON a.fid < b.fid
          AND a.xmin <= b.xmax AND a.xmax >= b.xmin
          AND a.ymin <= b.ymax AND a.ymax >= b.ymin
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02_boundary" AS
        SELECT fid, ST_Boundary(geom) AS boundary FROM "{dissolved}"
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02_touching" AS
        SELECT p.left_fid, p.right_fid
        FROM "{name}_02_pairs" p
        JOIN "{dissolved}" wl ON wl.fid = p.left_fid
        JOIN "{dissolved}" wr ON wr.fid = p.right_fid
        WHERE ST_Touches(wl.geom, wr.geom)
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02_shared" AS
        WITH raw AS (
            SELECT t.left_fid, t.right_fid,
                   ST_LineMerge(ST_CollectionExtract(
                       ST_Intersection(bl.boundary, br.boundary), 2
                   )) AS geom
            FROM "{name}_02_touching" t
            JOIN "{name}_02_boundary" bl ON bl.fid = t.left_fid
            JOIN "{name}_02_boundary" br ON br.fid = t.right_fid
        )
        SELECT left_fid, right_fid, geom FROM raw
        WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom)
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02_shared_by_fid" AS
        SELECT fid, ST_Union_Agg(geom) AS geom
        FROM (
            SELECT left_fid AS fid, geom FROM "{name}_02_shared"
            UNION ALL
            SELECT right_fid AS fid, geom FROM "{name}_02_shared"
        )
        GROUP BY fid
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02_exterior_raw" AS
        SELECT d.fid,
               ST_LineMerge(ST_Difference(
                   b.boundary, COALESCE(s.geom, {_EMPTY_LINES})
               )) AS geom
        FROM "{dissolved}" d
        JOIN "{name}_02_boundary" b ON b.fid = d.fid
        LEFT JOIN "{name}_02_shared_by_fid" s ON s.fid = d.fid
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02_shared_atomic" AS
        SELECT left_fid, right_fid, (dump).geom AS geom
        FROM "{name}_02_shared", UNNEST(ST_Dump(geom)) AS d(dump)
        WHERE NOT ST_IsEmpty((dump).geom)
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02_exterior" AS
        SELECT fid AS left_fid, NULL::BIGINT AS right_fid, (dump).geom AS geom
        FROM "{name}_02_exterior_raw", UNNEST(ST_Dump(geom)) AS d(dump)
        WHERE NOT ST_IsEmpty((dump).geom)
    """)

    classification = _classification_sql(levels, code_columns)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02" AS
        SELECT s.left_fid, s.right_fid, 'shared' AS boundary_type,
               {classification} AS "{depth_column}", s.geom
        FROM "{name}_02_shared_atomic" s
        JOIN "{dissolved}" l ON l.fid = s.left_fid
        JOIN "{dissolved}" r ON r.fid = s.right_fid

        UNION ALL BY NAME

        SELECT left_fid, right_fid, 'exterior' AS boundary_type,
               {min(levels)} AS "{depth_column}", geom
        FROM "{name}_02_exterior"
    """)

    _check_every_fid_present(conn, dissolved, f"{name}_02")

    for table in [
        "parts",
        "pairs",
        "boundary",
        "touching",
        "shared",
        "shared_by_fid",
        "exterior_raw",
        "shared_atomic",
        "exterior",
    ]:
        conn.execute(f'DROP TABLE IF EXISTS "{name}_02_{table}"')
