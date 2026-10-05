"""Tests for name-clean: safe fixes applied, everything else left for review."""

import duckdb
import pytest
from click.testing import CliRunner

from topo_tools.api.name_clean import clean
from topo_tools.cli.main import cli

_FIELDS = {"name_field": "adm{n}_name", "code_field": "adm{n}_code"}

_FILLER = ["Theta", "Iota", "Kappa", "Lambda", "Omicron", "Sigma", "Upsilon", "Phi"]

_NAMES = {
    "XY0101": " Gamma  ",
    "XY0102": "SÃ©gou",
    "XY0103": "Việt",
    "XY0104": "Del\u200bta",
    "XY0105": "RÍ\u008dO",
    "XY0106": "KING FAHAD CAUSWAY",
    "XY0107": "Alpha",
    "XY0108": "Alpha",
}

_FIXED = {
    "XY0101": "Gamma",
    "XY0102": "Ségou",
    "XY0103": "Việt",
    "XY0104": "Delta",
}


def _write(path):
    rows = list(_NAMES.items()) + [
        (f"XY01{i:02d}", n) for i, n in enumerate(_FILLER, start=20)
    ]
    values = ", ".join(
        f"('XY01', 'North', '{c}', '{n}', ST_Point({i}, 0))"
        for i, (c, n) in enumerate(rows)
    )
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        conn.execute(f"""
            CREATE TABLE t AS SELECT * FROM (VALUES {values})
            AS v(adm1_code, adm1_name, adm2_code, adm2_name, geom)
        """)
        conn.execute(f"COPY t TO '{path}'")


def _rows(path, columns):
    rel = duckdb.sql(f"SELECT {columns} FROM read_csv('{path}')")
    return [dict(zip(rel.columns, r, strict=True)) for r in rel.fetchall()]


@pytest.fixture
def names_input(tmp_path):
    path = tmp_path / "names.parquet"
    _write(path)
    return path


def test_safe_fixes_applied_rest_untouched(names_input, tmp_path):
    out = tmp_path / "clean.parquet"
    clean(names_input, out, tmp_path / "issues.csv", **_FIELDS)
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        names = dict(
            conn.execute(f"SELECT adm2_code, adm2_name FROM '{out}'").fetchall()
        )
        first = conn.execute(f"SELECT column_name FROM (DESCRIBE FROM '{out}')")
        assert first.fetchone()[0] == "geometry"
    assert len(names) == len(_NAMES) + len(_FILLER)
    for code, name in _NAMES.items():
        assert names[code] == _FIXED.get(code, name), code


def test_report_marks_fixed_rows(names_input, tmp_path):
    issues = tmp_path / "issues.csv"
    clean(names_input, tmp_path / "clean.parquet", issues, **_FIELDS)
    report = _rows(issues, "kind, code_a, fixed")
    fixed = {r["code_a"] for r in report if r["fixed"]}
    assert fixed == set(_FIXED)
    open_kinds = {r["kind"] for r in report if not r["fixed"]}
    assert open_kinds == {"case-outlier", "duplicate-name", "encoding-artifact"}


def test_default_paths(names_input):
    clean(names_input, **_FIELDS)
    assert (names_input.parent / "names_cleaned.parquet").exists()
    assert (names_input.parent / "names_name_issues.parquet").exists()


def test_steps(names_input, tmp_path):
    out = tmp_path / "clean.parquet"
    for step in ["inputs", "levels", "checks", "fix", "outputs"]:
        clean(
            names_input,
            out,
            tmp_path / "issues.csv",
            **_FIELDS,
            tmp_dir=tmp_path / "work",
            step=step,
        )
    assert out.exists()


def test_cli_help():
    result = CliRunner().invoke(cli, ["name-clean", "--help"])
    assert result.exit_code == 0
    assert "Fix the safe problems" in result.output
