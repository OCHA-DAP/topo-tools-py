"""Tests for the package() composite tool (polygons + points + lines in one call)."""

import duckdb
import pytest
import yaml
from click.testing import CliRunner

from topo_tools.api.package import package
from topo_tools.api.package_lines import package_lines
from topo_tools.api.package_points import package_points
from topo_tools.api.package_polygons import package_polygons
from topo_tools.cli.main import cli

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


def _write_schema(path, name_field, code_field):
    path.write_text(yaml.dump({"name_field": name_field, "code_field": code_field}))
    return path


@pytest.fixture
def admin2_input(tmp_path):
    path = tmp_path / "admin2.parquet"
    _write_synthetic(path, _ROWS)
    return path


@pytest.fixture
def pcode_target_schema(tmp_path):
    return _write_schema(
        tmp_path / "schema.yaml", name_field="adm{n}_name", code_field="adm{n}_pcode"
    )


def test_default_output_matches_calling_each_tool_separately(
    pcode_target_schema, tmp_path
):
    combined_dir = tmp_path / "combined"
    combined_dir.mkdir()
    combined_input = combined_dir / "admin2.parquet"
    _write_synthetic(combined_input, _ROWS)
    package(combined_input, target_schema_path=pcode_target_schema, overwrite=True)

    separate_dir = tmp_path / "separate"
    separate_dir.mkdir()
    separate_input = separate_dir / "admin2.parquet"
    _write_synthetic(separate_input, _ROWS)
    package_polygons(
        separate_input, target_schema_path=pcode_target_schema, overwrite=True
    )
    package_points(
        separate_input, target_schema_path=pcode_target_schema, overwrite=True
    )
    package_lines(
        separate_input, target_schema_path=pcode_target_schema, overwrite=True
    )

    combined_names = {p.name for p in combined_dir.glob("*.parquet")}
    separate_names = {p.name for p in separate_dir.glob("*.parquet")}
    assert combined_names == separate_names


def test_x_template_substitutes_per_subtool(
    admin2_input, pcode_target_schema, tmp_path
):
    template = str(tmp_path / "web_{x}.parquet")
    package(admin2_input, template, pcode_target_schema, overwrite=True)

    assert (tmp_path / "web_admin1.parquet").exists()
    assert (tmp_path / "web_admin2.parquet").exists()
    assert (tmp_path / "web_points.parquet").exists()
    assert (tmp_path / "web_lines.parquet").exists()


def test_missing_x_raises(admin2_input, pcode_target_schema, tmp_path):
    with pytest.raises(ValueError, match="literal '\\{x\\}'"):
        package(
            admin2_input,
            str(tmp_path / "flat.parquet"),
            pcode_target_schema,
            overwrite=True,
        )


def test_overwrite_and_target_schema_passed_through(
    admin2_input, pcode_target_schema, tmp_path
):
    template = str(tmp_path / "web_{x}.parquet")
    package(admin2_input, template, pcode_target_schema, overwrite=True)

    with pytest.raises(FileExistsError, match="already exists"):
        package(admin2_input, template, pcode_target_schema, overwrite=False)


def test_cli_default_naming(admin2_input, pcode_target_schema):
    result = CliRunner().invoke(
        cli, ["package", str(admin2_input), "--target-schema", str(pcode_target_schema)]
    )
    assert result.exit_code == 0, result.output
    assert admin2_input.with_stem(admin2_input.stem + "_admin1").exists()
    assert admin2_input.with_stem(admin2_input.stem + "_points").exists()
    assert admin2_input.with_stem(admin2_input.stem + "_lines").exists()


def test_cli_output_template(admin2_input, pcode_target_schema, tmp_path):
    result = CliRunner().invoke(
        cli,
        [
            "package",
            str(admin2_input),
            "--output",
            str(tmp_path / "web_{x}.parquet"),
            "--target-schema",
            str(pcode_target_schema),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "web_points.parquet").exists()
