"""Tests for name-detect: one fixture row per kind, report formats, steps."""

import duckdb
import pytest
from click.testing import CliRunner

from topo_tools.api.name_detect import detect
from topo_tools.cli.main import cli
from topo_tools.core.name_detect._03_checks import _CHECKS

_FIELDS = {"name_field": "adm{n}_name", "code_field": "adm{n}_code"}

_FILLER = ["Theta", "Iota", "Kappa", "Lambda", "Omicron", "Sigma", "Upsilon", "Phi"]

# Columns: adm1 code and name, adm2 code, name and Arabic name.
_ROWS = [
    ("XY01", "North", "XY0101", "Alpha", "ألفا"),
    ("XY01", "North", "XY0102", "Alpha", "ألفا"),
    ("XY01", "North", "XY0103", "Al-Beta", "بيتا"),
    ("XY01", "North", "XY0104", "al beta", "بيتا ٢"),
    ("XY01", "North", "XY0105", " Gamma  ", "غاما"),
    ("XY02", "South", "XY0201", "SÃ©gou", "سيغو"),
    ("XY02", "South", "XY0202", "Việt", "فيت"),
    ("XY02", "South", "XY0203", "Del\u200bta", "دلتا"),
    ("XY02", "South", "XY0204", "KING FAHAD CAUSWAY", "جسر"),
    ("XY02", "South", "XY0205", "K\u0430bul", "كابل"),
    ("XY02", "South", "XY0206", "Unknown", "مجهول"),
    ("XY02", "South", "XY0207", None, "فارغ"),
    ("XY02", "South", "XY0208", "Zeta XY0208", "زيتا"),
    ("XY02", "South2", "XY0209", "Eta", "إيتا"),
] + [
    ("XY02", "South", f"XY02{i:02d}", name, f"اسم {i}")
    for i, name in enumerate(_FILLER, start=10)
]

_EXPECTED = {
    "duplicate-name": ("XY0101", "warn"),
    "normalized-duplicate-name": ("XY0103", "warn"),
    "whitespace": ("XY0105", "warn"),
    "encoding-artifact": ("XY0201", "error"),
    "unnormalized-unicode": ("XY0202", "warn"),
    "invisible-character": ("XY0203", "warn"),
    "case-outlier": ("XY0204", "warn"),
    "mixed-script": ("XY0205", "warn"),
    "placeholder-name": ("XY0206", "error"),
    "blank-name": ("XY0207", "error"),
    "code-in-name": ("XY0208", "warn"),
}

_STEPS = ["inputs", "levels", "checks", "outputs"]


def _write(path, rows):
    values = ", ".join(
        "("
        + ", ".join(
            "NULL" if v is None else "'" + v.replace("'", "''") + "'" for v in r
        )
        + f", ST_Point({i}, 0))"
        for i, r in enumerate(rows)
    )
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        conn.execute(f"""
            CREATE TABLE t AS SELECT * FROM (VALUES {values})
            AS v(adm1_code, adm1_name, adm2_code, adm2_name, adm2_name1, geom)
        """)
        conn.execute(f"COPY t TO '{path}'")


def _read(path):
    reader = "read_csv" if path.suffix == ".csv" else "read_parquet"
    rel = (
        duckdb.sql(f"SELECT * EXCLUDE (geometry) FROM {reader}('{path}')")
        if (path.suffix == ".parquet")
        else duckdb.sql(f"SELECT * FROM {reader}('{path}')")
    )
    return [dict(zip(rel.columns, row, strict=True)) for row in rel.fetchall()]


@pytest.fixture
def names_input(tmp_path):
    path = tmp_path / "names.parquet"
    _write(path, _ROWS)
    return path


def test_cli_help():
    result = CliRunner().invoke(cli, ["name-detect", "--help"])
    assert result.exit_code == 0
    assert "Find problems in the unit names of one coded layer." in result.output
    assert "Examples:" in result.output


def test_every_kind(names_input, tmp_path):
    out = tmp_path / "issues.csv"
    detect(names_input, out, **_FIELDS)
    report = _read(out)
    found = {(r["kind"], r["code_a"], r["severity"]) for r in report}
    for kind, (code, severity) in _EXPECTED.items():
        assert (kind, code, severity) in found, kind
    assert {r["kind"] for r in report} == set(_EXPECTED)


def test_duplicate_reported_once_across_language_columns(names_input, tmp_path):
    out = tmp_path / "issues.csv"
    detect(names_input, out, **_FIELDS)
    report = _read(out)
    assert sum(r["kind"] == "duplicate-name" for r in report) == 1


def test_suggested_fixes(names_input, tmp_path):
    out = tmp_path / "issues.csv"
    detect(names_input, out, **_FIELDS)
    suggested = {r["code_a"]: r["suggested"] for r in _read(out)}
    assert suggested["XY0105"] == "Gamma"
    assert suggested["XY0201"] == "Ségou"
    assert suggested["XY0202"] == "Việt"
    assert suggested["XY0203"] == "Delta"


def test_unsafe_repair_is_flagged_without_suggestion(tmp_path):
    path = tmp_path / "bad.parquet"
    rows = [
        ("XY01", "North", f"XY01{i:02d}", n, f"اسم {i}") for i, n in enumerate(_FILLER)
    ]
    rows.append(("XY01", "North", "XY0199", "R\u00cd\u008dO", "نهر"))
    _write(path, rows)
    out = tmp_path / "issues.csv"
    detect(path, out, **_FIELDS)
    found = {r["kind"]: r["suggested"] for r in _read(out)}
    assert found == {"encoding-artifact": None}


def test_clean_names_write_empty_report(tmp_path):
    path = tmp_path / "clean.parquet"
    _write(
        path,
        [
            ("XY01", "North", f"XY01{i:02d}", n, f"اسم {i}")
            for i, n in enumerate(_FILLER)
        ],
    )
    out = tmp_path / "issues.csv"
    detect(path, out, **_FIELDS)
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")
    assert _read(out) == []


def test_column_wide_kind_rolls_up(tmp_path):
    path = tmp_path / "spaced.parquet"
    _write(
        path,
        [
            ("XY01", "North", f"XY01{i:02d}", f"{n} ", f"اسم {i}")
            for i, n in enumerate(_FILLER)
        ],
    )
    out = tmp_path / "issues.csv"
    detect(path, out, **_FIELDS)
    report = _read(out)
    assert len(report) == 1
    assert report[0]["kind"] == "whitespace"
    assert report[0]["code_a"] is None
    assert report[0]["reason"].startswith("8 of 8 names")


def test_parquet_report_has_geometry(names_input, tmp_path):
    out = tmp_path / "issues.parquet"
    detect(names_input, out, **_FIELDS)
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        first, missing = conn.execute(
            f"SELECT (SELECT column_name FROM (DESCRIBE FROM '{out}') LIMIT 1), "
            f"COUNT(*) FILTER (WHERE geometry IS NULL) FROM '{out}'"
        ).fetchone()
    assert first == "geometry"
    assert missing == 0


def test_structural_detection(tmp_path):
    # A parent with two names breaks the hierarchy structural detection reads.
    path = tmp_path / "names.parquet"
    _write(path, [r for r in _ROWS if r[1] != "South2"])
    out = tmp_path / "issues.csv"
    detect(path, out)
    assert "case-outlier" in {r["kind"] for r in _read(out)}


def test_default_issues_path(names_input):
    detect(names_input, **_FIELDS)
    assert (names_input.parent / "names_name_issues.parquet").exists()


def test_bad_issues_suffix_raises(names_input, tmp_path):
    with pytest.raises(ValueError, match="issues_path must end in"):
        detect(names_input, tmp_path / "issues.gpkg", **_FIELDS)


def test_failing_check_reported_others_run(names_input, tmp_path, monkeypatch):
    def broken(_source):
        return "SELECT * FROM missing_table"

    monkeypatch.setitem(_CHECKS, "whitespace", broken)
    out = tmp_path / "issues.csv"
    detect(names_input, out, **_FIELDS)
    rows = _read(out)
    kinds = {r["kind"] for r in rows}
    assert "whitespace" not in kinds
    assert "case-outlier" in kinds
    (failed,) = [r for r in rows if r["kind"] == "check-failed"]
    assert failed["severity"] == "error"
    assert failed["reason"].startswith("whitespace check failed:")


def test_cli_error_on_existing_output(names_input, tmp_path):
    out = tmp_path / "issues.csv"
    out.write_text("x")
    result = CliRunner().invoke(
        cli, ["name-detect", str(names_input), str(out), "--overwrite", "false"]
    )
    assert result.exit_code != 0
    assert "output already exists" in result.output


def test_steps(names_input, tmp_path):
    out = tmp_path / "issues.csv"
    for step in _STEPS:
        detect(names_input, out, **_FIELDS, tmp_dir=tmp_path / "work", step=step)
    assert "case-outlier" in {r["kind"] for r in _read(out)}


def _report_for(tmp_path, names):
    path = tmp_path / "pairs.parquet"
    rows = [
        ("XY01", "North", f"XY01{i:02d}", n, f"اسم {i}")
        for i, n in enumerate(_FILLER + names)
    ]
    _write(path, rows)
    out = tmp_path / "issues.csv"
    detect(path, out, **_FIELDS)
    return {(r["kind"], r["name_a"]) for r in _read(out)}


def test_accents_fold_only_against_unaccented_latin(tmp_path):
    found = _report_for(
        tmp_path, ["Segou", "Ségou", "Mỹ Tho", "Mỹ Thọ", "ကူကြီး", "ကံကြီး"]
    )
    kinds = [k for k, _ in found if k == "normalized-duplicate-name"]
    assert kinds == ["normalized-duplicate-name"]
    assert ("normalized-duplicate-name", "Segou") in found


def test_case_ignores_caseless_scripts_and_acronyms(tmp_path):
    mixed = ["Rho", "Chi", "Psi", "Tau", "Beta", "Delta", "Zeta", "Eta", "Mu", "Nu"]
    acronyms = ["S.P.S.M.", "KCCA", "UEP II", "BARMM"]
    found = _report_for(tmp_path, [*mixed, "ქარელის", *acronyms, "CHARI BAGUIRMI"])
    assert {n for k, n in found if k == "case-outlier"} == {"CHARI BAGUIRMI"}


def test_mojibake_lookalike_is_not_flagged(tmp_path):
    found = _report_for(tmp_path, ["LOM\u00c9\u00a0COMMUNE", "FAN\u00d8\u2013ESBJERG"])
    assert not {k for k, _ in found} & {"encoding-artifact"}


def test_code_in_name_needs_a_whole_pcode_token(tmp_path):
    path = tmp_path / "codes.parquet"
    rows = [("XY01", "North", f"LAG{i}", n, f"اسم {i}") for i, n in enumerate(_FILLER)]
    rows += [("XY01", "North", "LAG", "LAGOS", "لاغوس")]
    rows += [("XY01", "North", "XY0199", "Zeta XY0199", "زيتا")]
    _write(path, rows)
    out = tmp_path / "issues.csv"
    detect(path, out, **_FIELDS)
    found = {r["code_a"] for r in _read(out) if r["kind"] == "code-in-name"}
    assert found == {"XY0199"}


def test_uncoded_units_are_not_reported(tmp_path):
    path = tmp_path / "nocode.parquet"
    rows = [
        ("XY01", "North", f"XY01{i:02d}", n, f"اسم {i}") for i, n in enumerate(_FILLER)
    ]
    rows += [("XY01", "North", None, None, None), ("XY01", "North", None, "Rho", None)]
    _write(path, rows)
    out = tmp_path / "issues.csv"
    detect(path, out, **_FIELDS)
    assert _read(out) == []


def test_numbered_names_are_not_normalized_duplicates(tmp_path):
    found = _report_for(tmp_path, ["Ward 1-2", "Ward 12", "Zone I-II", "Zone III"])
    assert not [k for k, _ in found if k == "normalized-duplicate-name"]


def test_quoted_column_names(tmp_path):
    path = tmp_path / "quoted.parquet"
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        conn.execute(f"""
            COPY (SELECT 'XY01' AS "a'd""m1_code", 'North' AS "a'd""m1_name",
                         ' x' AS other, ST_Point(0, 0) AS geom) TO '{path}'
        """)
    out = tmp_path / "issues.parquet"
    detect(path, out, name_field="a'd\"m{n}_name", code_field="a'd\"m{n}_code")
    assert _read(out) == []


def test_placeholder_variants(tmp_path):
    found = _report_for(tmp_path, ["N_A", "undefined"])
    assert {n for k, n in found if k == "placeholder-name"} == {"N_A", "undefined"}
