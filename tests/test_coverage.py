"""Unit tests for core/coverage.py's width-aware gap and micro-polygon checking."""

import duckdb
import pytest

from topo_tools.core.constants import SNAP_TOLERANCE
from topo_tools.core.coverage import (
    check_valid_topology,
    count_gaps,
    coverage_clean,
    has_gaps,
    has_micro_polygons,
    merge_micro_polygons,
)


def _write_polygon_with_hole(conn, hole_width):
    """One polygon: a 3x3 square with a centered hole_width square hole cut out."""
    w = hole_width
    lo, hi = 1.5 - w / 2, 1.5 + w / 2
    wkt = (
        f"POLYGON((0 0, 3 0, 3 3, 0 3, 0 0), "
        f"({lo} {lo}, {hi} {lo}, {hi} {hi}, {lo} {hi}, {lo} {lo}))"
    )
    conn.execute(
        "CREATE OR REPLACE TABLE synth AS "
        f"SELECT 1 AS fid, ST_GeomFromText('{wkt}') AS geom"
    )


def test_has_gaps_tolerates_wide_hole_when_scoped():
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        _write_polygon_with_hole(conn, hole_width=2.0)
        assert has_gaps(conn, "synth", gap_maximum_width=0)
        assert not has_gaps(conn, "synth", gap_maximum_width=SNAP_TOLERANCE)


def test_check_valid_topology_raises_on_micro_gap_even_when_scoped():
    """A gap at/below SNAP_TOLERANCE must still raise: only wider gaps are tolerated."""
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        _write_polygon_with_hole(conn, hole_width=SNAP_TOLERANCE / 2)
        with pytest.raises(RuntimeError, match="GAPS"):
            check_valid_topology(conn, "synth", gap_maximum_width=SNAP_TOLERANCE)


def test_check_valid_topology_tolerates_wide_gap_when_scoped():
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        _write_polygon_with_hole(conn, hole_width=2.0)
        check_valid_topology(conn, "synth", gap_maximum_width=SNAP_TOLERANCE)


def test_count_gaps_respects_min_width():
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        _write_polygon_with_hole(conn, hole_width=2.0)
        assert count_gaps(conn, "synth") == 1
        assert count_gaps(conn, "synth", min_width=SNAP_TOLERANCE) == 1
        assert count_gaps(conn, "synth", min_width=3.0) == 0


SLIVER = SNAP_TOLERANCE / 10
SQUARE_A = "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
SQUARE_B = "POLYGON((1 0, 2 0, 2 1, 1 1, 1 0))"


def _strip(x0, width, height=0.5):
    """Return a width-wide, height-tall rectangle at x0 as WKT ring text."""
    x1 = x0 + width
    return f"(({x0} 0, {x1} 0, {x1} {height}, {x0} {height}, {x0} 0))"


def _merge(rows):
    """Load (fid, wkt) rows, run merge_micro_polygons, return (count, out, issues)."""
    conn = duckdb.connect()
    conn.execute("INSTALL spatial; LOAD spatial;")
    values = ", ".join(f"({fid}, '{wkt}')" for fid, wkt in rows)
    conn.execute(
        "CREATE TABLE synth AS SELECT fid, ST_GeomFromText(wkt) AS geom "
        f"FROM (VALUES {values}) v(fid, wkt)"
    )
    count = merge_micro_polygons(conn, "synth", "out", issues_table="issues")
    out = dict(
        conn.execute(
            "SELECT fid, ST_NumGeometries(geom) FROM out ORDER BY fid"
        ).fetchall()
    )
    issues = conn.execute(
        "SELECT unit_a, unit_b, reason, fixed FROM issues ORDER BY key"
    ).fetchall()
    assert not has_micro_polygons(conn, "out")
    return count, out, issues


def test_micro_polygon_raises_in_check_valid_topology():
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        wkt = f"MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)), {_strip(5, SLIVER)})"
        conn.execute(f"CREATE TABLE synth AS SELECT 1 AS fid, '{wkt}'::GEOMETRY geom")
        assert has_micro_polygons(conn, "synth")
        with pytest.raises(RuntimeError, match="MICRO_POLYGONS"):
            check_valid_topology(conn, "synth")


def test_overlap_sliver_merges_into_the_feature_it_overlaps():
    wkt_a = f"MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)), {_strip(1, SLIVER)})"
    count, out, issues = _merge([(1, wkt_a), (2, SQUARE_B)])
    assert count == 1
    assert out == {1: 1, 2: 1}
    assert issues == [(1, 2, "merged into neighbouring feature", True)]


def test_touching_fragment_merges_into_its_own_large_part():
    wkt_a = f"MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)), {_strip(1, SLIVER)})"
    count, out, issues = _merge([(1, wkt_a)])
    assert count == 1
    assert out == {1: 1}
    assert issues == [(1, 1, "merged into neighbouring feature", True)]


def test_isolated_fragment_is_dropped_and_large_part_kept():
    wkt_a = f"MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)), {_strip(5, SLIVER)})"
    count, out, issues = _merge([(1, wkt_a), (2, SQUARE_B)])
    assert count == 1
    assert out == {1: 1, 2: 1}
    assert issues == [(1, None, "dropped: touches no feature", True)]


def test_whole_micro_feature_row_is_removed():
    wkt_c = "POLYGON" + _strip(2, SLIVER)
    count, out, issues = _merge([(1, SQUARE_A), (2, SQUARE_B), (3, wkt_c)])
    assert count == 1
    assert out == {1: 1, 2: 1}
    assert issues == [(3, 2, "merged into neighbouring feature", True)]


def test_small_real_island_is_kept():
    island = _strip(5, SNAP_TOLERANCE * 10, height=SNAP_TOLERANCE * 10)
    wkt_a = f"MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)), {island})"
    count, out, issues = _merge([(1, wkt_a)])
    assert count == 0
    assert out == {1: 2}
    assert issues == []


def test_coverage_clean_removes_whole_micro_feature_instead_of_emptying_it():
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        wkt_c = "POLYGON" + _strip(2, SLIVER, height=1)
        conn.execute(
            "CREATE TABLE synth AS SELECT fid, ST_GeomFromText(wkt) AS geom FROM "
            f"(VALUES (1, '{SQUARE_A}'), (2, '{SQUARE_B}'), (3, '{wkt_c}')) v(fid, wkt)"
        )
        coverage_clean(conn, "synth", "out", fids=None, micro_issues_table="micro")
        rows = conn.execute("SELECT fid, ST_IsEmpty(geom) FROM out ORDER BY fid")
        assert rows.fetchall() == [(1, False), (2, False)]
        assert conn.execute("SELECT unit_a, unit_b FROM micro").fetchall() == [(3, 2)]
