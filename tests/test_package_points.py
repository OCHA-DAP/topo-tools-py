"""Correctness + portability tests for the package_points() tool."""

import duckdb
import pytest
from click.testing import CliRunner

from topo_tools.api.package_points import package_points
from topo_tools.cli.main import cli

_STEPS = ["inputs", "points", "outputs"]

_ROWS = [
    {
        "adm1_pcode": "P1",
        "adm2_pcode": "A1",
        "wkt": "POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))",
    },
    {
        "adm1_pcode": "P1",
        "adm2_pcode": "A2",
        "wkt": "POLYGON((10 0, 10 10, 20 10, 20 0, 10 0))",
    },
    {
        "adm1_pcode": "P2",
        "adm2_pcode": "B1",
        "wkt": "POLYGON((0 10, 0 20, 10 20, 10 10, 0 10))",
    },
]


def _sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return f"'{value}'"
    return str(value)


def _write_synthetic(path, rows: list[dict]) -> None:
    cols = [k for k in rows[0] if k != "wkt"]
    col_list = ", ".join([*cols, "geom"])
    values = ", ".join(
        "("
        + ", ".join(_sql_literal(r[c]) for c in cols)
        + f", ST_GeomFromText('{r['wkt']}'))"
        for r in rows
    )
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        conn.execute(
            f"CREATE TABLE synth AS SELECT * FROM (VALUES {values}) AS t({col_list})"
        )
        conn.execute(f"COPY synth TO '{path}'")


@pytest.fixture
def admin2_input(tmp_path):
    path = tmp_path / "admin2.parquet"
    _write_synthetic(path, _ROWS)
    return path


def test_cli_help():
    result = CliRunner().invoke(cli, ["package-points", "--help"])
    assert result.exit_code == 0
    assert "label point" in result.output
    assert "Examples:" in result.output


def test_row_count_matches_units_per_level(admin2_input, tmp_path):
    output_path = tmp_path / "points.parquet"
    package_points(
        admin2_input,
        output_path,
        name_field="adm{n}_name",
        code_field="adm{n}_pcode",
        overwrite=True,
    )

    with duckdb.connect() as conn:
        conn.execute("LOAD spatial")
        counts = dict(
            conn.execute(
                f"SELECT adm_lvl, COUNT(*) FROM '{output_path}' GROUP BY adm_lvl"
            ).fetchall()
        )
    expected_level1_count = 2
    expected_level2_count = 3
    assert counts == {1: expected_level1_count, 2: expected_level2_count}


def test_every_point_covered_by_its_own_polygon(admin2_input, tmp_path):
    output_path = tmp_path / "points.parquet"
    package_points(
        admin2_input,
        output_path,
        name_field="adm{n}_name",
        code_field="adm{n}_pcode",
        overwrite=True,
    )

    with duckdb.connect() as conn:
        conn.execute("LOAD spatial")
        uncovered = conn.execute(f"""
            SELECT COUNT(*) FROM '{output_path}' p
            JOIN '{admin2_input}' src
              ON src.adm2_pcode IS NOT DISTINCT FROM p.adm2_pcode
            WHERE p.adm_lvl = 2
              AND NOT ST_Covers(ST_SetCRS(src.geom, 'EPSG:4326'), p.geometry)
        """).fetchone()[0]
    assert uncovered == 0


def test_original_attribute_columns_survive(admin2_input, tmp_path):
    output_path = tmp_path / "points.parquet"
    package_points(
        admin2_input,
        output_path,
        name_field="adm{n}_name",
        code_field="adm{n}_pcode",
        overwrite=True,
    )

    with duckdb.connect() as conn:
        conn.execute("LOAD spatial")
        columns = {
            row[0]
            for row in conn.execute(
                f"DESCRIBE SELECT * FROM '{output_path}'"
            ).fetchall()
        }
    assert {"adm1_pcode", "adm2_pcode", "adm_lvl", "geometry"} <= columns


def test_custom_depth_column(admin2_input, tmp_path):
    output_path = tmp_path / "points.parquet"
    package_points(
        admin2_input,
        output_path,
        name_field="adm{n}_name",
        code_field="adm{n}_pcode",
        depth_column="level",
        overwrite=True,
    )
    with duckdb.connect() as conn:
        conn.execute("LOAD spatial")
        columns = {
            row[0]
            for row in conn.execute(
                f"DESCRIBE SELECT * FROM '{output_path}'"
            ).fetchall()
        }
    assert "level" in columns
    assert "adm_lvl" not in columns


def test_depth_column_collision_raises(tmp_path):
    rows = [{**r, "adm_lvl": 2} for r in _ROWS]
    input_path = tmp_path / "admin2.parquet"
    _write_synthetic(input_path, rows)
    with pytest.raises(ValueError, match="adm_lvl"):
        package_points(
            input_path,
            tmp_path / "points.parquet",
            name_field="adm{n}_name",
            code_field="adm{n}_pcode",
        )


def test_step_reuse(admin2_input, tmp_path):
    output_path = tmp_path / "points.parquet"
    work_dir = tmp_path / "work"
    for step in _STEPS:
        package_points(
            admin2_input,
            output_path,
            name_field="adm{n}_name",
            code_field="adm{n}_pcode",
            tmp_dir=work_dir,
            step=step,
            overwrite=True,
        )
    assert output_path.exists()


def test_default_output_path(admin2_input):
    package_points(
        admin2_input,
        name_field="adm{n}_name",
        code_field="adm{n}_pcode",
        overwrite=True,
    )
    expected = admin2_input.with_stem(admin2_input.stem + "_points")
    assert expected.exists()


def test_cli_overwrite_false_raises_on_existing_output(admin2_input, tmp_path):
    output_path = tmp_path / "points.parquet"
    output_path.touch()
    result = CliRunner().invoke(
        cli,
        [
            "package-points",
            str(admin2_input),
            str(output_path),
            "--name-field",
            "adm{n}_name",
            "--code-field",
            "adm{n}_pcode",
            "--overwrite=false",
        ],
    )
    assert result.exit_code != 0
    assert "output already exists" in result.output
