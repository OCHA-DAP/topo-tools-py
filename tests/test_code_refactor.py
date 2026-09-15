"""Portability + naming tests for the code_refactor() tool."""

import duckdb
import pytest
from click.testing import CliRunner

from topo_tools.api.code_refactor import code_refactor
from topo_tools.cli.main import cli

_MIN_WIDTH = 3


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


def _fetch(path, columns: str, order_by: str):
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        return conn.execute(
            f"SELECT {columns} FROM '{path}' ORDER BY {order_by}"
        ).fetchall()


def test_cli_help():
    result = CliRunner().invoke(cli, ["code-refactor", "--help"])
    assert result.exit_code == 0
    assert "Cold-start a hierarchical code" in result.output


def test_gadm_style_cold_start_admin0_passthrough(tmp_path):
    """Example A: GID_0 is constant, dropped structurally, left untouched."""
    rows = [
        {
            "GID_0": "AFG",
            "GID_1": "AFG.1_1",
            "NAME_1": "Badakhshan",
            "GID_2": "AFG.1.1_1",
            "NAME_2": "Arghanj Khwa",
            "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        },
        {
            "GID_0": "AFG",
            "GID_1": "AFG.1_1",
            "NAME_1": "Badakhshan",
            "GID_2": "AFG.1.2_1",
            "NAME_2": "Baharak",
            "wkt": "POLYGON((1 0, 2 0, 2 1, 1 1, 1 0))",
        },
        {
            "GID_0": "AFG",
            "GID_1": "AFG.2_1",
            "NAME_1": "Badghis",
            "GID_2": "AFG.2.1_1",
            "NAME_2": "Ab Kamari",
            "wkt": "POLYGON((0 1, 1 1, 1 2, 0 2, 0 1))",
        },
    ]
    input_path = tmp_path / "admin2.parquet"
    _write_synthetic(input_path, rows)

    output_path = tmp_path / "admin2_coded.parquet"
    code_refactor(input_path, output_path, root_code="AFG", delimiter=".", min_width=3)

    result = _fetch(output_path, "GID_0, GID_1, NAME_1, GID_2, NAME_2", "GID_1, GID_2")
    assert result == [
        ("AFG", "AFG.001", "Badakhshan", "AFG.001.001", "Arghanj Khwa"),
        ("AFG", "AFG.001", "Badakhshan", "AFG.001.002", "Baharak"),
        ("AFG", "AFG.002", "Badghis", "AFG.002.001", "Ab Kamari"),
    ]


def test_word_per_level_naming(tmp_path):
    """Example B: state_code/county_code, no adm{n} template needed."""
    rows = [
        {
            "state_code": "TX",
            "county_code": "TX-HARRIS",
            "county_name": "Harris",
            "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        },
        {
            "state_code": "TX",
            "county_code": "TX-DALLAS",
            "county_name": "Dallas",
            "wkt": "POLYGON((1 0, 2 0, 2 1, 1 1, 1 0))",
        },
        {
            "state_code": "CA",
            "county_code": "CA-ORANGE",
            "county_name": "Orange",
            "wkt": "POLYGON((0 1, 1 1, 1 2, 0 2, 0 1))",
        },
    ]
    input_path = tmp_path / "states.parquet"
    _write_synthetic(input_path, rows)

    output_path = tmp_path / "states_coded.parquet"
    code_refactor(input_path, output_path, root_code="USA", delimiter=".", min_width=3)

    result = _fetch(output_path, "state_code, county_code, county_name", "county_code")
    assert result == [
        ("USA.001", "USA.001.001", "Orange"),
        ("USA.002", "USA.002.001", "Dallas"),
        ("USA.002", "USA.002.002", "Harris"),
    ]


def test_explicit_code_name_field_overrides_ambiguous_auto_detection(tmp_path):
    """Example C: two code-shaped columns per level, --code-field breaks the tie."""
    rows = [
        {
            "adm0_code": "AFG",
            "adm1_code": "NAT-01",
            "adm1_pcode": "PC-01",
            "adm1_name": "Badakhshan",
            "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        },
        {
            "adm0_code": "AFG",
            "adm1_code": "NAT-02",
            "adm1_pcode": "PC-02",
            "adm1_name": "Badghis",
            "wkt": "POLYGON((1 0, 2 0, 2 1, 1 1, 1 0))",
        },
    ]
    input_path = tmp_path / "ambiguous.parquet"
    _write_synthetic(input_path, rows)

    output_path = tmp_path / "ambiguous_coded.parquet"
    code_refactor(
        input_path,
        output_path,
        root_code="AFG",
        delimiter=".",
        min_width=3,
        code_field="adm{n}_pcode",
        name_field="adm{n}_name",
    )

    result = _fetch(
        output_path, "adm0_code, adm1_code, adm1_pcode, adm1_name", "adm1_pcode"
    )
    assert result == [
        ("AFG", "NAT-01", "AFG.001", "Badakhshan"),
        ("AFG", "NAT-02", "AFG.002", "Badghis"),
    ]


def test_overflow_writes_four_digit_code_and_issues_row(tmp_path):
    """Example D: >999 children, no repad of the first 999, issues row written."""
    total = 1200
    rows = [
        {
            "adm0_code": "BRA",
            "adm1_code": f"BRA-{i:04d}",
            "wkt": f"POLYGON(({i} 0, {i + 1} 0, {i + 1} 1, {i} 1, {i} 0))",
        }
        for i in range(total)
    ]
    input_path = tmp_path / "overflow.parquet"
    _write_synthetic(input_path, rows)

    output_path = tmp_path / "overflow_coded.parquet"
    issues_path = tmp_path / "overflow_issues.csv"
    code_refactor(
        input_path,
        output_path,
        issues_path,
        root_code="BRA",
        delimiter=".",
        min_width=3,
    )

    codes = {r[0] for r in _fetch(output_path, "adm1_code", "adm1_code")}
    assert len(codes) == total
    assert "BRA.999" in codes
    assert "BRA.1000" in codes
    assert all(
        len(c.split(".")[-1]) == _MIN_WIDTH
        for c in codes
        if int(c.split(".")[-1]) <= 999  # noqa: PLR2004
    )

    with duckdb.connect() as conn:
        issue = conn.execute(
            f"SELECT kind, level, parent_code, child_count, min_width "
            f"FROM '{issues_path}'"
        ).fetchone()
    assert issue == ("digit-overflow", 1, "BRA", total, 3)


def test_disputed_territory_root_code_is_opaque(tmp_path):
    """Example E: a non-ISO3 user-assigned root code works with no special casing."""
    rows = [
        {
            "region_code": "K1",
            "region_name": "North Kosovo",
            "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        },
        {
            "region_code": "K2",
            "region_name": "South Kosovo",
            "wkt": "POLYGON((1 0, 2 0, 2 1, 1 1, 1 0))",
        },
    ]
    input_path = tmp_path / "kosovo_disputed.parquet"
    _write_synthetic(input_path, rows)

    output_path = tmp_path / "kosovo_coded.parquet"
    code_refactor(input_path, output_path, root_code="XKO", delimiter=".", min_width=3)

    result = _fetch(output_path, "region_code, region_name", "region_code")
    assert result == [
        ("XKO.001", "North Kosovo"),
        ("XKO.002", "South Kosovo"),
    ]


_TWO_LEVEL_ROWS = [
    {
        "adm1_code": "P1",
        "adm2_code": "P1-01",
        "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
    },
    {
        "adm1_code": "P1",
        "adm2_code": "P1-02",
        "wkt": "POLYGON((1 0, 2 0, 2 1, 1 1, 1 0))",
    },
    {
        "adm1_code": "P2",
        "adm2_code": "P2-01",
        "wkt": "POLYGON((0 1, 1 1, 1 2, 0 2, 0 1))",
    },
]


def test_custom_delimiter_and_width(tmp_path):
    input_path = tmp_path / "custom.parquet"
    _write_synthetic(input_path, _TWO_LEVEL_ROWS)

    output_path = tmp_path / "custom_coded.parquet"
    code_refactor(input_path, output_path, root_code="AA", delimiter="-", min_width=2)

    codes = {r[0] for r in _fetch(output_path, "adm1_code", "adm1_code")}
    assert codes == {"AA-01", "AA-02"}


def test_mismatched_code_name_field_raises(tmp_path):
    rows = [
        {"adm1_code": "A1", "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"},
    ]
    input_path = tmp_path / "one.parquet"
    _write_synthetic(input_path, rows)
    with pytest.raises(ValueError, match="must be given together"):
        code_refactor(
            input_path,
            root_code="AA",
            delimiter=".",
            min_width=3,
            code_field="adm{n}_code",
        )


def test_default_output_path(tmp_path):
    input_path = tmp_path / "leaf.parquet"
    _write_synthetic(input_path, _TWO_LEVEL_ROWS)
    code_refactor(input_path, root_code="AA", delimiter=".", min_width=3)
    assert input_path.with_stem(input_path.stem + "_coded").exists()


def test_steps(tmp_path):
    input_path = tmp_path / "leaf.parquet"
    _write_synthetic(input_path, _TWO_LEVEL_ROWS)

    output_path = tmp_path / "steps_out.parquet"
    work_dir = tmp_path / "work"
    for step in ("inputs", "levels", "assign", "outputs"):
        code_refactor(
            input_path,
            output_path,
            root_code="AA",
            delimiter=".",
            min_width=3,
            tmp_dir=work_dir,
            step=step,
            overwrite=True,
        )
    assert output_path.exists()


def test_cli_error_on_existing_output(tmp_path):
    rows = [
        {"adm1_code": "A1", "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"},
    ]
    input_path = tmp_path / "leaf.parquet"
    _write_synthetic(input_path, rows)
    output_path = tmp_path / "exists.parquet"
    output_path.touch()
    result = CliRunner().invoke(
        cli,
        [
            "code-refactor",
            str(input_path),
            str(output_path),
            "--root-code",
            "AA",
            "--delimiter",
            ".",
            "--min-width",
            "3",
            "--overwrite=false",
        ],
    )
    assert result.exit_code != 0
    assert "output already exists" in result.output
