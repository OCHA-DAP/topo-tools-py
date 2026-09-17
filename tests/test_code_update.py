"""Retention-policy tests for the code_update() tool."""

import duckdb
import pytest
from click.testing import CliRunner

from topo_tools.api.code_refactor import code_refactor
from topo_tools.api.code_update import code_update
from topo_tools.cli.main import cli

_CHANGELOG_COLUMNS = [
    "level",
    "old_code",
    "old_name",
    "new_code",
    "new_name",
    "relationship_class",
    "cluster_id",
    "match_method",
    "code_outcome",
    "reason",
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


def _fetch(path, columns: str, order_by: str):
    with duckdb.connect() as conn:
        conn.execute("INSTALL spatial; LOAD spatial;")
        return conn.execute(
            f"SELECT {columns} FROM '{path}' ORDER BY {order_by}"
        ).fetchall()


def _read_changelog(path) -> list[dict]:
    with duckdb.connect() as conn:
        rows = conn.execute(f"SELECT * FROM '{path}'").fetchall()
    return [dict(zip(_CHANGELOG_COLUMNS, r, strict=True)) for r in rows]


def _rows_where(rows: list[dict], **kwargs) -> list[dict]:
    return [r for r in rows if all(r[k] == v for k, v in kwargs.items())]


def test_cli_help():
    result = CliRunner().invoke(cli, ["code-update", "--help"])
    assert result.exit_code == 0
    assert "Reconcile an already-coded OLD layer" in result.output


_ALL_CLASSES_OLD_ROWS = [
    {
        "adm1_pcode": "AA.001",
        "adm1_name": "N1",
        "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
    },
    {
        "adm1_pcode": "AA.002",
        "adm1_name": "N2",
        "wkt": "POLYGON((10 0, 11 0, 11 1, 10 1, 10 0))",
    },
    {
        "adm1_pcode": "AA.003",
        "adm1_name": "N3",
        "wkt": "POLYGON((20 0, 21 0, 21 1, 20 1, 20 0))",
    },
    {
        "adm1_pcode": "AA.004",
        "adm1_name": "N4",
        "wkt": "POLYGON((30 0, 33 0, 33 1, 30 1, 30 0))",
    },
    {
        "adm1_pcode": "AA.005",
        "adm1_name": "N5a",
        "wkt": "POLYGON((40 0, 41 0, 41 1, 40 1, 40 0))",
    },
    {
        "adm1_pcode": "AA.006",
        "adm1_name": "N5b",
        "wkt": "POLYGON((41 0, 43 0, 43 1, 41 1, 41 0))",
    },
    {
        "adm1_pcode": "AA.007",
        "adm1_name": "N7",
        "wkt": "POLYGON((60 0, 61 0, 61 1, 60 1, 60 0))",
    },
    {
        "adm1_pcode": "AA.008",
        "adm1_name": "RL8",
        "wkt": "POLYGON((70 0, 71 0, 71 1, 70 1, 70 0))",
    },
    {
        "adm1_pcode": "AA.009",
        "adm1_name": "CX1",
        "wkt": "POLYGON((80 0, 82 0, 82 2, 80 2, 80 0))",
    },
    {
        "adm1_pcode": "AA.010",
        "adm1_name": "CX2",
        "wkt": "POLYGON((82 0, 84 0, 84 2, 82 2, 82 0))",
    },
]
_ALL_CLASSES_NEW_ROWS = [
    {
        "adm1_pcode": "x1",
        "adm1_name": "N1",
        "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
    },
    {
        "adm1_pcode": "x2",
        "adm1_name": "N2 Renamed",
        "wkt": "POLYGON((10 0, 11 0, 11 1, 10 1, 10 0))",
    },
    {
        "adm1_pcode": "x3",
        "adm1_name": "N3",
        "wkt": "POLYGON((20 0, 21 0, 21 0.9, 20 0.9, 20 0))",
    },
    {
        "adm1_pcode": "x4a",
        "adm1_name": "N4a",
        "wkt": "POLYGON((30 0, 31 0, 31 1, 30 1, 30 0))",
    },
    {
        "adm1_pcode": "x4b",
        "adm1_name": "N4b",
        "wkt": "POLYGON((31 0, 33 0, 33 1, 31 1, 31 0))",
    },
    {
        "adm1_pcode": "x5",
        "adm1_name": "N5",
        "wkt": "POLYGON((40 0, 43 0, 43 1, 40 1, 40 0))",
    },
    {
        "adm1_pcode": "x9",
        "adm1_name": "C1",
        "wkt": "POLYGON((50 0, 51 0, 51 1, 50 1, 50 0))",
    },
    {
        "adm1_pcode": "x8",
        "adm1_name": "RL8",
        "wkt": "POLYGON((70.9 0, 71.9 0, 71.9 1, 70.9 1, 70.9 0))",
    },
    {
        "adm1_pcode": "x10",
        "adm1_name": "CXA",
        "wkt": "POLYGON((80 0, 84 0, 84 1, 80 1, 80 0))",
    },
    {
        "adm1_pcode": "x11",
        "adm1_name": "CXB",
        "wkt": "POLYGON((80 1, 84 1, 84 2, 80 2, 80 1))",
    },
]
_EXPECTED_SPLIT_COUNT = 2
_EXPECTED_COMPLEX_COUNT = 2


@pytest.fixture
def all_classes_result(tmp_path):
    """One spatially-separated region per relationship_class (or class pair)."""
    old_path = tmp_path / "old.parquet"
    new_path = tmp_path / "new.parquet"
    _write_synthetic(old_path, _ALL_CLASSES_OLD_ROWS)
    _write_synthetic(new_path, _ALL_CLASSES_NEW_ROWS)

    output_path = tmp_path / "new_coded.parquet"
    changelog_path = tmp_path / "changelog.csv"
    code_update(
        old_path,
        new_path,
        output_path,
        changelog_path,
        root_code="AA",
        delimiter=".",
        min_width=3,
        name_field_a="adm{n}_name",
        code_field_a="adm{n}_pcode",
        name_field_b="adm{n}_name",
        code_field_b="adm{n}_pcode",
        link_by_name=True,
        tau_match=0.4,
    )

    rows = _read_changelog(changelog_path)
    predecessor_by_code = dict(
        _fetch(output_path, "adm1_pcode, predecessor_code", "adm1_pcode")
    )
    return rows, predecessor_by_code


def test_unchanged_retains_code(all_classes_result):
    rows, _ = all_classes_result
    unchanged = _rows_where(rows, relationship_class="unchanged")
    assert len(unchanged) == 1
    assert unchanged[0]["old_code"] == "AA.001"
    assert unchanged[0]["new_code"] == "AA.001"
    assert unchanged[0]["code_outcome"] == "retained"


def test_renamed_retains_code_and_updates_name(all_classes_result):
    rows, _ = all_classes_result
    renamed = _rows_where(rows, relationship_class="renamed")
    assert len(renamed) == 1
    assert renamed[0]["old_code"] == "AA.002"
    assert renamed[0]["new_code"] == "AA.002"
    assert renamed[0]["new_name"] == "N2 Renamed"
    assert renamed[0]["code_outcome"] == "retained"


def test_modified_gets_new_code_with_predecessor(all_classes_result):
    rows, predecessor_by_code = all_classes_result
    modified = _rows_where(rows, relationship_class="modified")
    assert len(modified) == 1
    assert modified[0]["old_code"] == "AA.003"
    assert modified[0]["code_outcome"] == "new"
    assert predecessor_by_code[modified[0]["new_code"]] == "AA.003"


def test_split_shares_cluster_and_predecessor(all_classes_result):
    rows, predecessor_by_code = all_classes_result
    split = _rows_where(rows, relationship_class="split")
    assert len(split) == _EXPECTED_SPLIT_COUNT
    assert len({r["cluster_id"] for r in split}) == 1
    assert all(r["old_code"] is None for r in split)
    assert all(r["code_outcome"] == "new" for r in split)
    for r in split:
        assert predecessor_by_code[r["new_code"]] == "AA.004"


def test_merge_retires_both_olds_no_predecessor_on_survivor(all_classes_result):
    rows, predecessor_by_code = all_classes_result
    merge_retired = _rows_where(
        rows, relationship_class="merge", code_outcome="retired"
    )
    merge_new = _rows_where(rows, relationship_class="merge", code_outcome="new")
    assert {r["old_code"] for r in merge_retired} == {"AA.005", "AA.006"}
    assert len(merge_new) == 1
    assert len({r["cluster_id"] for r in [*merge_retired, *merge_new]}) == 1
    assert predecessor_by_code[merge_new[0]["new_code"]] is None


def test_removed_has_no_new_code(all_classes_result):
    rows, _ = all_classes_result
    removed = _rows_where(rows, relationship_class="removed")
    assert len(removed) == 1
    assert removed[0]["old_code"] == "AA.007"
    assert removed[0]["new_code"] is None
    assert removed[0]["code_outcome"] == "retired"


def test_created_has_no_predecessor(all_classes_result):
    rows, predecessor_by_code = all_classes_result
    created = _rows_where(rows, relationship_class="created")
    assert len(created) == 1
    assert created[0]["old_code"] is None
    assert created[0]["code_outcome"] == "new"
    assert predecessor_by_code[created[0]["new_code"]] is None


def test_relocated_identity_linked_with_predecessor(all_classes_result):
    rows, predecessor_by_code = all_classes_result
    relocated = _rows_where(rows, relationship_class="relocated")
    assert len(relocated) == 1
    assert relocated[0]["old_code"] == "AA.008"
    assert relocated[0]["code_outcome"] == "new"
    assert relocated[0]["match_method"] == "identity"
    assert predecessor_by_code[relocated[0]["new_code"]] == "AA.008"


def test_complex_cluster_retires_olds_no_predecessor_on_survivors(all_classes_result):
    rows, predecessor_by_code = all_classes_result
    complex_retired = _rows_where(
        rows, relationship_class="complex", code_outcome="retired"
    )
    complex_new = _rows_where(rows, relationship_class="complex", code_outcome="new")
    assert {r["old_code"] for r in complex_retired} == {"AA.009", "AA.010"}
    assert len(complex_new) == _EXPECTED_COMPLEX_COUNT
    assert len({r["cluster_id"] for r in [*complex_retired, *complex_new]}) == 1
    assert all(predecessor_by_code[r["new_code"]] is None for r in complex_new)


def test_multilevel_cascade_rewrites_unchanged_children_under_new_parent(tmp_path):
    """A modified level-1 parent cascades its new prefix to unchanged descendants."""
    old_rows = [
        {
            "adm1_pcode": "AA.001",
            "adm1_name": "Province1",
            "adm2_pcode": "AA.001.001",
            "adm2_name": "District1",
            "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        },
        {
            "adm1_pcode": "AA.001",
            "adm1_name": "Province1",
            "adm2_pcode": "AA.001.002",
            "adm2_name": "District2",
            "wkt": "POLYGON((1 0, 2 0, 2 1, 1 1, 1 0))",
        },
        {
            "adm1_pcode": "AA.001",
            "adm1_name": "Province1",
            "adm2_pcode": "AA.001.003",
            "adm2_name": "District3",
            "wkt": "POLYGON((2 0, 3 0, 3 1, 2 1, 2 0))",
        },
        {
            "adm1_pcode": "AA.002",
            "adm1_name": "Province2",
            "adm2_pcode": "AA.002.001",
            "adm2_name": "OnlyDistrict",
            "wkt": "POLYGON((10 10, 11 10, 11 11, 10 11, 10 10))",
        },
    ]
    new_rows = [
        {
            "adm1_pcode": "x",
            "adm1_name": "Province1",
            "adm2_pcode": "y1",
            "adm2_name": "District1",
            "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        },
        {
            "adm1_pcode": "x",
            "adm1_name": "Province1",
            "adm2_pcode": "y2",
            "adm2_name": "District2",
            "wkt": "POLYGON((1 0, 2 0, 2 1, 1 1, 1 0))",
        },
        {
            "adm1_pcode": "x",
            "adm1_name": "Province1",
            "adm2_pcode": "y3",
            "adm2_name": "District3 Expanded",
            "wkt": "POLYGON((2 0, 3 0, 3 3, 2 3, 2 0))",
        },
        {
            "adm1_pcode": "z",
            "adm1_name": "Province2",
            "adm2_pcode": "y4",
            "adm2_name": "OnlyDistrict",
            "wkt": "POLYGON((10 10, 11 10, 11 11, 10 11, 10 10))",
        },
    ]
    old_path = tmp_path / "old.parquet"
    new_path = tmp_path / "new.parquet"
    _write_synthetic(old_path, old_rows)
    _write_synthetic(new_path, new_rows)

    output_path = tmp_path / "new_coded.parquet"
    changelog_path = tmp_path / "changelog.csv"
    code_update(
        old_path,
        new_path,
        output_path,
        changelog_path,
        root_code="AA",
        delimiter=".",
        min_width=3,
        name_field_a="adm{n}_name",
        code_field_a="adm{n}_pcode",
        name_field_b="adm{n}_name",
        code_field_b="adm{n}_pcode",
    )

    rows = _read_changelog(changelog_path)

    level1 = _rows_where(rows, level=1)
    province1 = _rows_where(level1, old_code="AA.001")[0]
    province2 = _rows_where(level1, old_code="AA.002")[0]
    assert province1["relationship_class"] == "modified"
    assert province1["code_outcome"] == "new"
    assert province2["relationship_class"] == "unchanged"
    assert province2["new_code"] == "AA.002"

    new_province1_code = province1["new_code"]
    assert new_province1_code != "AA.001"

    level2 = _rows_where(rows, level=2)
    d1 = _rows_where(level2, old_code="AA.001.001")[0]
    d2 = _rows_where(level2, old_code="AA.001.002")[0]
    d3 = _rows_where(level2, old_code="AA.001.003")[0]
    d4 = _rows_where(level2, old_code="AA.002.001")[0]

    assert d1["relationship_class"] == "unchanged"
    assert d1["new_code"] == f"{new_province1_code}.001"
    assert d2["relationship_class"] == "unchanged"
    assert d2["new_code"] == f"{new_province1_code}.002"
    assert d3["relationship_class"] == "modified"
    assert d3["new_code"].startswith(f"{new_province1_code}.")
    assert d4["relationship_class"] == "unchanged"
    assert d4["new_code"] == "AA.002.001"

    out_codes = {r[0] for r in _fetch(output_path, "adm1_pcode", "adm1_pcode")}
    assert out_codes == {new_province1_code, "AA.002"}


def test_level_count_mismatch_raises(tmp_path):
    old_rows = [
        {
            "adm1_pcode": "AA.001",
            "adm1_name": "P1",
            "adm2_pcode": "AA.001.001",
            "adm2_name": "D1",
            "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        },
    ]
    new_rows = [
        {
            "adm1_pcode": "x",
            "adm1_name": "P1",
            "wkt": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        },
    ]
    old_path = tmp_path / "old.parquet"
    new_path = tmp_path / "new.parquet"
    _write_synthetic(old_path, old_rows)
    _write_synthetic(new_path, new_rows)

    with pytest.raises(ValueError, match="level mismatch"):
        code_update(
            old_path,
            new_path,
            tmp_path / "out.parquet",
            tmp_path / "changelog.csv",
            root_code="AA",
            delimiter=".",
            min_width=3,
            name_field_a="adm{n}_name",
            code_field_a="adm{n}_pcode",
            name_field_b="adm{n}_name",
            code_field_b="adm{n}_pcode",
        )


def test_custom_format_round_trip_detected_from_old_codes(tmp_path):
    """code-update auto-detects a code-refactor-produced custom delimiter/width."""
    raw_rows = [
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
    raw_path = tmp_path / "raw.parquet"
    _write_synthetic(raw_path, raw_rows)

    old_coded_path = tmp_path / "old_coded.parquet"
    code_refactor(raw_path, old_coded_path, root_code="AA", delimiter="-", min_width=2)

    new_path = tmp_path / "new.parquet"
    _write_synthetic(new_path, raw_rows)

    output_path = tmp_path / "new_coded.parquet"
    changelog_path = tmp_path / "changelog.csv"
    code_update(old_coded_path, new_path, output_path, changelog_path)

    level1_codes = {r[0] for r in _fetch(output_path, "adm1_code", "adm1_code")}
    level2_codes = {r[0] for r in _fetch(output_path, "adm2_code", "adm2_code")}
    assert level1_codes == {"AA-01", "AA-02"}
    assert level2_codes == {"AA-01-01", "AA-01-02", "AA-02-01"}

    rows = _read_changelog(changelog_path)
    assert all(r["relationship_class"] == "unchanged" for r in rows)
    assert all(r["code_outcome"] == "retained" for r in rows)
