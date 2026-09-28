"""Smoke tests for schema-map's default mode (map, then apply) and its modes."""

import csv

import duckdb
import pytest
from click.testing import CliRunner

from topo_tools.api.schema_map import map as schema_map
from topo_tools.cli.main import cli

_STEPS = ["inputs", "map", "apply", "outputs"]


def _write_table(path, col_names, rows):
    def _cell(col, val):
        if col == "geom":
            return f"ST_GeomFromText('{val}')"
        return "NULL" if val is None else f"'{val}'"

    values = ", ".join(
        "(" + ", ".join(_cell(c, v) for c, v in zip(col_names, row, strict=True)) + ")"
        for row in rows
    )
    cols_decl = ", ".join(col_names)
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        conn.execute(
            f"CREATE TABLE synth AS SELECT * FROM (VALUES {values}) AS t({cols_decl})"
        )
        conn.execute(f"COPY synth TO '{path}'")


def _unit_square(i):
    return f"POLYGON(({i} 0, {i + 1} 0, {i + 1} 1, {i} 1, {i} 0))"


def _crosswalk_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return {row["source_column"]: row for row in csv.DictReader(f)}


@pytest.fixture
def structural_hierarchy_input(tmp_path):
    """GRID3-style hierarchy (name/code pairs, two levels) plus GIS noise columns."""
    path = tmp_path / "structural.parquet"
    rows = [
        (
            _unit_square(0),
            "Province One",
            "PU1",
            "Zone Alpha",
            "PU1ZU1",
            "1",
            "1.5",
            "2.5",
        ),
        (
            _unit_square(1),
            "Province One",
            "PU1",
            "Zone Beta",
            "PU1ZU2",
            "2",
            "1.5",
            "2.5",
        ),
        (
            _unit_square(2),
            "Province Two",
            "PU2",
            "Zone Gamma",
            "PU2ZU3",
            "3",
            "1.5",
            "2.5",
        ),
        (
            _unit_square(3),
            "Province Two",
            "PU2",
            "Zone Delta",
            "PU2ZU4",
            "4",
            "1.5",
            "2.5",
        ),
    ]
    _write_table(
        path,
        [
            "geom",
            "province",
            "prov_uid",
            "zonesante",
            "zs_uid",
            "OBJECTID",
            "Shape_Length",
            "Shape_Area",
        ],
        rows,
    )
    return path


def test_cli_help():
    result = CliRunner().invoke(cli, ["schema-map", "--help"])
    assert result.exit_code == 0
    assert "--map-only" in result.output
    assert "Examples:" in result.output


def test_end_to_end_writes_crosswalk_and_mapped_output(
    structural_hierarchy_input, tmp_path
):
    crosswalk_out = tmp_path / "out_crosswalk.csv"
    mapped_out = tmp_path / "out_mapped.parquet"
    schema_map(
        structural_hierarchy_input,
        mapped_out,
        csv_output=crosswalk_out,
        name_field="adm{n}_name",
        code_field="adm{n}_pcode",
        overwrite=True,
    )

    rows = _crosswalk_rows(crosswalk_out)
    assert rows["province"]["target_column"] == "adm1_name"
    assert rows["province"]["note"] == ""
    assert rows["prov_uid"]["target_column"] == "adm1_pcode"
    assert rows["prov_uid"]["note"] == ""
    assert rows["zonesante"]["target_column"] == "adm2_name"
    assert rows["zs_uid"]["target_column"] == "adm2_pcode"
    assert "OBJECTID" not in rows
    assert "Shape_Length" not in rows

    with duckdb.connect() as conn:
        conn.execute("LOAD spatial")
        columns = {
            r[0]
            for r in conn.execute(f"DESCRIBE SELECT * FROM '{mapped_out}'").fetchall()
        }
        values = conn.execute(
            f"SELECT adm2_name FROM '{mapped_out}' ORDER BY adm2_pcode"
        ).fetchall()
    assert columns == {
        "adm1_name",
        "adm1_pcode",
        "adm2_name",
        "adm2_pcode",
        "geometry",
    }
    assert values == [
        ("Zone Alpha",),
        ("Zone Beta",),
        ("Zone Gamma",),
        ("Zone Delta",),
    ]


def test_default_output_paths(structural_hierarchy_input):
    schema_map(
        structural_hierarchy_input,
        name_field="adm{n}_name",
        code_field="adm{n}_pcode",
        overwrite=True,
    )

    expected_mapped = structural_hierarchy_input.with_stem(
        structural_hierarchy_input.stem + "_mapped"
    )
    expected_crosswalk = structural_hierarchy_input.with_stem(
        structural_hierarchy_input.stem + "_crosswalk"
    ).with_suffix(".csv")
    assert expected_mapped.exists()
    assert expected_crosswalk.exists()


def test_overwrite_required_for_both_outputs(structural_hierarchy_input, tmp_path):
    crosswalk_out = tmp_path / "out_crosswalk.csv"
    mapped_out = tmp_path / "out_mapped.parquet"
    schema_map(
        structural_hierarchy_input,
        mapped_out,
        csv_output=crosswalk_out,
        name_field="adm{n}_name",
        code_field="adm{n}_pcode",
    )

    with pytest.raises(FileExistsError, match="output already exists"):
        schema_map(
            structural_hierarchy_input,
            mapped_out,
            csv_output=crosswalk_out,
            name_field="adm{n}_name",
            code_field="adm{n}_pcode",
            overwrite=False,
        )

    schema_map(
        structural_hierarchy_input,
        mapped_out,
        csv_output=crosswalk_out,
        name_field="adm{n}_name",
        code_field="adm{n}_pcode",
    )


def test_cli_error_on_existing_output(structural_hierarchy_input, tmp_path):
    mapped_out = tmp_path / "exists.parquet"
    mapped_out.touch()
    result = CliRunner().invoke(
        cli,
        [
            "schema-map",
            str(structural_hierarchy_input),
            str(mapped_out),
            "--name-field",
            "adm{n}_name",
            "--code-field",
            "adm{n}_pcode",
            "--overwrite=false",
        ],
    )
    assert result.exit_code != 0
    assert "output already exists" in result.output


def test_crosswalk_steps(structural_hierarchy_input, tmp_path):
    mapped_out = tmp_path / "steps_mapped.parquet"
    crosswalk_out = tmp_path / "steps_crosswalk.csv"
    work_dir = tmp_path / "work"
    for step in _STEPS:
        schema_map(
            structural_hierarchy_input,
            mapped_out,
            csv_output=crosswalk_out,
            name_field="adm{n}_name",
            code_field="adm{n}_pcode",
            tmp_dir=work_dir,
            step=step,
            overwrite=True,
        )
    assert mapped_out.exists()
    assert crosswalk_out.exists()


def test_map_only_writes_crosswalk_only(structural_hierarchy_input, tmp_path):
    crosswalk_out = tmp_path / "out_crosswalk.csv"
    schema_map(structural_hierarchy_input, csv_output=crosswalk_out, map_only=True)

    assert crosswalk_out.read_bytes().startswith(b"\xef\xbb\xbf")
    assert not structural_hierarchy_input.with_stem(
        structural_hierarchy_input.stem + "_mapped"
    ).exists()


def test_csv_input_writes_mapped_layer_only(structural_hierarchy_input, tmp_path):
    crosswalk_out = tmp_path / "out_crosswalk.csv"
    schema_map(structural_hierarchy_input, csv_output=crosswalk_out, map_only=True)
    crosswalk_out.rename(tmp_path / "edited.csv")

    mapped_out = tmp_path / "out_mapped.parquet"
    schema_map(
        structural_hierarchy_input,
        mapped_out,
        csv_input=tmp_path / "edited.csv",
    )

    assert mapped_out.exists()
    assert not crosswalk_out.exists()
    assert (
        not structural_hierarchy_input.with_stem(
            structural_hierarchy_input.stem + "_crosswalk"
        )
        .with_suffix(".csv")
        .exists()
    )


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        (
            {"csv_input": "x.csv", "map_only": True},
            "csv_input and map_only",
        ),
        (
            {"csv_input": "x.csv", "csv_output": "y.csv"},
            "csv_input and csv_output",
        ),
        ({"csv_input": "x.csv", "level": 2}, "csv_input and level"),
        (
            {"output_path": "out.parquet", "map_only": True},
            "map_only and output_path",
        ),
        ({"output_path": "out.csv"}, "is a CSV"),
        ({"map_only": True, "step": "apply"}, "step must be one of"),
        ({"csv_input": "x.csv", "step": "map"}, "step must be one of"),
    ],
)
def test_invalid_mode_arguments_raise(structural_hierarchy_input, kwargs, match):
    with pytest.raises(ValueError, match=match):
        schema_map(structural_hierarchy_input, **kwargs)


def test_cli_csv_output_points_to_csv_output(structural_hierarchy_input, tmp_path):
    result = CliRunner().invoke(
        cli, ["schema-map", str(structural_hierarchy_input), str(tmp_path / "x.csv")]
    )
    assert result.exit_code != 0
    assert "--csv-output" in result.output
