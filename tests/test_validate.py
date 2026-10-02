"""Tests for validate: stage reports, the summary, skips, failures and exit codes."""

import sys

import duckdb
import pytest
from click.testing import CliRunner

from topo_tools.api.validate import validate
from topo_tools.cli.main import cli

_FIELDS = {"name_field": "adm{n}_name", "code_field": "adm{n}_pcode"}


def _write(path, select: str = "SELECT * FROM base"):
    """Three levels: 3 regions, 9 districts, 27 communes, as adjacent squares."""
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        conn.execute("""--sql
            CREATE TABLE base AS
            SELECT 'XY' || a AS adm1_pcode, 'Region ' || a AS adm1_name,
                   'XY' || a || b AS adm2_pcode, 'District ' || a || b AS adm2_name,
                   'XY' || a || b || c AS adm3_pcode,
                   'Commune ' || a || b || c AS adm3_name,
                   ST_MakeEnvelope((a - 1) * 3 + b - 1, c - 1, (a - 1) * 3 + b, c)
                       AS geom
            FROM range(1, 4) r1(a), range(1, 4) r2(b), range(1, 4) r3(c)
        """)
        conn.execute(f"COPY ({select}) TO '{path}'")
    return path


def _summary(path):
    rel = duckdb.sql(f"SELECT * FROM read_csv('{path}', all_varchar = true)")
    return [dict(zip(rel.columns, row, strict=True)) for row in rel.fetchall()]


_DUPLICATE = """--sql
    SELECT * REPLACE (CASE WHEN adm3_pcode = 'XY112' THEN 'XY111'
                           ELSE adm3_pcode END AS adm3_pcode)
    FROM base
"""
_OUTLIER = """--sql
    SELECT * REPLACE (CASE WHEN adm3_pcode = 'XY111' THEN 'XY11-1'
                           ELSE adm3_pcode END AS adm3_pcode)
    FROM base
"""


def test_cli_help():
    result = CliRunner().invoke(cli, ["validate", "--help"])
    assert result.exit_code == 0
    assert "Check one layer with every detect tool" in result.output


def test_clean_layer(tmp_path):
    assert not validate(_write(tmp_path / "in.parquet"), tmp_path / "out")
    for suffix in ["schema_issues.csv", "code_issues.csv", "name_issues.csv"]:
        assert (tmp_path / "out" / f"in_{suffix}").exists()
    summary = tmp_path / "out" / "in_validate_summary.csv"
    assert summary.read_bytes().startswith(b"\xef\xbb\xbf")
    rows = _summary(summary)
    assert [r["stage"] for r in rows] == ["schema", "topo", "code", "name"]
    assert {r["reason"] for r in rows} == {"no issues"}


def test_reports_default_beside_input(tmp_path):
    validate(_write(tmp_path / "layer.parquet"))
    assert (tmp_path / "layer_validate_summary.csv").exists()
    assert (tmp_path / "layer_code_issues.csv").exists()


def test_error_counted_in_summary(tmp_path):
    assert validate(_write(tmp_path / "in.parquet", _DUPLICATE), tmp_path, **_FIELDS)
    rows = _summary(tmp_path / "in_validate_summary.csv")
    assert {
        "stage": "code",
        "kind": "duplicate-code",
        "severity": "error",
        "count": "1",
        "report": str(tmp_path / "in_code_issues.csv"),
        "reason": None,
    } in rows


def test_undetected_levels_skip_code_and_name(tmp_path):
    select = "SELECT adm3_name AS label, geom FROM base"
    assert validate(_write(tmp_path / "in.parquet", select), tmp_path)
    rows = {
        (r["stage"], r["kind"], r["severity"])
        for r in _summary(tmp_path / "in_validate_summary.csv")
    }
    assert ("schema", "levels-undetected", "error") in rows
    assert {("code", "skipped", "warn"), ("name", "skipped", "warn")} <= rows
    assert not (tmp_path / "in_code_issues.csv").exists()


def test_failing_stage_recorded_others_run(tmp_path, monkeypatch):
    def broken(*_args, **_kwargs):
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(sys.modules["topo_tools.api.validate"], "topo_detect", broken)
    assert validate(_write(tmp_path / "in.parquet"), tmp_path)
    rows = _summary(tmp_path / "in_validate_summary.csv")
    topo = [r for r in rows if r["stage"] == "topo"]
    assert topo == [
        {
            "stage": "topo",
            "kind": "failed",
            "severity": "error",
            "count": None,
            "report": None,
            "reason": "boom",
        }
    ]
    assert {r["stage"] for r in rows} == {"schema", "topo", "code", "name"}


def test_existing_report_without_overwrite_raises(tmp_path):
    path = _write(tmp_path / "in.parquet")
    (tmp_path / "in_name_issues.csv").touch()
    with pytest.raises(FileExistsError):
        validate(path, overwrite=False)
    assert not (tmp_path / "in_schema_issues.csv").exists()


@pytest.mark.parametrize(
    ("select", "exit_code"),
    [("SELECT * FROM base", 0), (_OUTLIER, 0), (_DUPLICATE, 1)],
    ids=["clean", "warnings", "errors"],
)
def test_cli_exit_code(tmp_path, select, exit_code):
    path = _write(tmp_path / "in.parquet", select)
    fields = ["--name-field", "adm{n}_name", "--code-field", "adm{n}_pcode"]
    result = CliRunner().invoke(cli, ["validate", str(path), *fields])
    assert result.exit_code == exit_code
