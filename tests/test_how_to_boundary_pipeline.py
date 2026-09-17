"""Runs the how-to guide's command sequence against its committed fixtures."""

import csv
from pathlib import Path

import duckdb
import pytest

from topo_tools.api.code_refactor import code_refactor
from topo_tools.api.edge_match import match
from topo_tools.api.package import package
from topo_tools.api.package_polygons import package_polygons
from topo_tools.api.schema_fill import fill
from topo_tools.api.schema_map import map as schema_map
from topo_tools.api.schema_refactor import refactor
from topo_tools.api.topo_clean import clean

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_DISTRICT_RAW = _FIXTURES_DIR / "how_to_district_raw.parquet"
_NEIGHBORHOOD_RAW = _FIXTURES_DIR / "how_to_neighborhood_raw.parquet"


def _rows(path, columns="*") -> list[tuple]:
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        return conn.execute(f"SELECT {columns} FROM '{path}'").fetchall()


@pytest.fixture
def pipeline(tmp_path):
    """Run stages 1-3 (schema, topology, codes) once; stages 4-6 branch from here."""
    crosswalk_path = tmp_path / "crosswalk.csv"
    schema_map(_DISTRICT_RAW, crosswalk_path)

    with crosswalk_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row["source_column"] == "LOCAL_REF":
            assert row["target_column"] == "adm1_code1", (
                "fixture no longer reproduces the cardinality-decoy mismatch"
            )
            row["target_column"] = ""
    with crosswalk_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    mapped_path = tmp_path / "district_mapped.parquet"
    refactor(_DISTRICT_RAW, crosswalk_path, mapped_path)

    topo_path = tmp_path / "district_topo.parquet"
    issues_path = tmp_path / "district_topo_issues.parquet"
    clean(mapped_path, topo_path, issues_path, maximum_gap_width="all")

    coded_path = tmp_path / "district_coded.parquet"
    code_refactor(topo_path, coded_path, root_code="TT", delimiter=".", min_width=2)

    return tmp_path, coded_path


def test_schema_map_reproduces_cardinality_decoy(tmp_path):
    crosswalk_path = tmp_path / "crosswalk.csv"
    schema_map(_DISTRICT_RAW, crosswalk_path)
    with crosswalk_path.open(newline="") as f:
        rows = {row["source_column"]: row["target_column"] for row in csv.DictReader(f)}
    assert rows["PCODE_2"] == "adm1_code"
    assert rows["LOCAL_REF"] == "adm1_code1"
    assert rows["NAME_2"] == "adm1_name"
    assert rows["NAME_1"] == "adm0_name"
    assert rows["PCODE_1"] == "adm0_code"


def test_schema_refactor_drops_decoy_column(pipeline):
    tmp_path, _ = pipeline
    mapped_path = tmp_path / "district_mapped.parquet"
    columns = {
        c[0]
        for c in duckdb.connect()
        .execute(f"DESCRIBE SELECT * FROM '{mapped_path}'")
        .fetchall()
    }
    assert columns == {"geometry", "adm0_name", "adm0_code", "adm1_name", "adm1_code"}


def test_topo_clean_fixes_one_gap_and_one_overlap(pipeline):
    tmp_path, _ = pipeline
    issues_path = tmp_path / "district_topo_issues.parquet"
    kinds = sorted(r[0] for r in _rows(issues_path, "kind"))
    assert kinds == ["gap", "overlap"]
    assert all(r[0] for r in _rows(issues_path, "fixed"))


def test_code_refactor_assigns_nested_codes(pipeline):
    _, coded_path = pipeline
    rows = dict(_rows(coded_path, "adm1_name, adm1_code"))
    assert rows["Riverside"] == "TT.02.04"
    assert rows["North Ridge"] == "TT.01.01"
    province_codes = {r[0] for r in _rows(coded_path, "adm0_code")}
    assert province_codes == {"TT.01", "TT.02"}


def test_edge_match_fills_neighborhood_wedge(pipeline, tmp_path):
    _, coded_path = pipeline
    parent_path = tmp_path / "riverside_parent.parquet"
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        conn.execute(
            f"COPY (SELECT * FROM '{coded_path}' WHERE adm1_code = 'TT.02.04') "
            f"TO '{parent_path}'"
        )

    matched_path = tmp_path / "neighborhood_matched.parquet"
    issues_path = tmp_path / "neighborhood_matched_issues.parquet"
    match(_NEIGHBORHOOD_RAW, parent_path, matched_path, issues_path)

    assert not issues_path.exists()
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        union_area = conn.execute(
            f"SELECT ST_Area(ST_Union_Agg(geometry)) FROM '{matched_path}'"
        ).fetchone()[0]
        parent_area = conn.execute(
            f"SELECT ST_Area(geometry) FROM '{parent_path}'"
        ).fetchone()[0]
    assert union_area == pytest.approx(parent_area)


def test_schema_fill_and_package_polygons_derive_provinces(pipeline, tmp_path):
    _, coded_path = pipeline
    filled_path = tmp_path / "district_filled.parquet"
    fill(coded_path, filled_path)
    package_polygons(filled_path)

    admin0_path = tmp_path / "district_filled_admin0.parquet"
    provinces = dict(_rows(admin0_path, "adm0_code, adm0_name"))
    assert provinces == {"TT.01": "Alpha Province", "TT.02": "Beta Province"}


def test_package_produces_full_bundle(pipeline, tmp_path):
    _, coded_path = pipeline
    output_dir = tmp_path / "release"
    package(coded_path, output_path=str(output_dir / "{x}.parquet"))

    assert (output_dir / "admin0.parquet").exists()
    assert (output_dir / "admin1.parquet").exists()
    points = _rows(output_dir / "points.parquet", "adm_lvl")
    assert sorted(points) == [(0,)] * 2 + [(1,)] * 8
