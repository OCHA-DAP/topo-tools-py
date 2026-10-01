"""Unit tests for core.code's pure functions: format, cascade, rewrite, detection."""

import duckdb
import pytest

from topo_tools.core.code import (
    CodeFormat,
    assign_new_codes,
    build_code,
    detect_code_format,
    detect_undelimited_format,
    has_delimiter,
    last_component,
    next_available_integer,
    parent_prefix,
    parse_code,
    parse_min_width,
    resolve_code_format,
    rewrite_child_code,
)

_MIN_WIDTH = 3
_FMT = CodeFormat(root_code="AFG", delimiter=".", min_width=_MIN_WIDTH)


def test_resolve_code_format_validates():
    with pytest.raises(ValueError, match="non-empty"):
        resolve_code_format("", ".", 3)
    with pytest.raises(ValueError, match="single character"):
        resolve_code_format("AFG", "::", 3)
    with pytest.raises(ValueError, match="positive"):
        resolve_code_format("AFG", ".", 0)
    assert resolve_code_format("AFG", ".", 3) == _FMT


def test_parse_build_round_trip():
    code = "AFG.001.002"
    parts = parse_code(code, _FMT)
    assert parts == ["AFG", "001", "002"]
    assert build_code(parts, _FMT) == code
    assert parent_prefix(code, _FMT) == "AFG.001"
    assert last_component(code, _FMT) == "002"


def test_parent_prefix_raises_on_root_only():
    with pytest.raises(ValueError, match="no parent"):
        parent_prefix("AFG", _FMT)


def test_next_available_integer_ignores_nested_and_nonnumeric():
    existing = ["AFG.001", "AFG.002", "AFG.002.001", "AFG.xx", "AFH.999"]
    assert next_available_integer(existing, "AFG", _FMT) == _MIN_WIDTH


def test_next_available_integer_empty_starts_at_one():
    assert next_available_integer([], "AFG", _FMT) == 1


def test_rewrite_child_code_keeps_tail_reattaches_prefix():
    assert rewrite_child_code("AFG.001.002", "AFG.005", _FMT) == "AFG.005.002"


def test_assign_new_codes_ranks_gappy_nonnumeric_duplicated_source():
    with duckdb.connect() as conn:
        conn.execute("""
            CREATE TABLE t (
                id_col INTEGER, parent_code VARCHAR, sort_col VARCHAR, code_col VARCHAR
            )
        """)
        conn.executemany(
            "INSERT INTO t VALUES (?, ?, ?, ?)",
            [
                (1, "AFG", "zz", None),
                (2, "AFG", "5", None),
                (3, "AFG", "5", None),
                (4, "AFG", "aa", None),
            ],
        )
        assign_new_codes(
            conn,
            "t",
            id_column="id_col",
            parent_column="parent_code",
            sort_columns=["sort_col"],
            code_column="code_col",
            fmt=_FMT,
            level=1,
        )
        codes = [r[0] for r in conn.execute("SELECT code_col FROM t").fetchall()]
    assert sorted(codes) == ["AFG.001", "AFG.002", "AFG.003", "AFG.004"]
    assert "AFG.zz" not in codes
    assert "AFG.5" not in codes


def test_assign_new_codes_overflow_no_repad_of_first_999():
    total = 1200
    with duckdb.connect() as conn:
        conn.execute("""
            CREATE TABLE t (
                id_col INTEGER, parent_code VARCHAR, sort_col INTEGER, code_col VARCHAR
            )
        """)
        conn.executemany(
            "INSERT INTO t VALUES (?, ?, ?, ?)",
            [(i, "BRA", i, None) for i in range(1, total + 1)],
        )
        assign_new_codes(
            conn,
            "t",
            id_column="id_col",
            parent_column="parent_code",
            sort_columns=["sort_col"],
            code_column="code_col",
            fmt=CodeFormat(root_code="BRA", delimiter=".", min_width=_MIN_WIDTH),
            level=1,
        )
        by_rank = dict(conn.execute("SELECT sort_col, code_col FROM t").fetchall())
    assert by_rank[1] == "BRA.001"
    assert by_rank[999] == "BRA.999"
    assert by_rank[1000] == "BRA.1000"
    assert all(len(by_rank[i].split(".")[-1]) == _MIN_WIDTH for i in range(1, 1000))


def test_assign_new_codes_continues_from_existing_codes():
    with duckdb.connect() as conn:
        conn.execute("""
            CREATE TABLE t (
                id_col INTEGER, parent_code VARCHAR, sort_col INTEGER, code_col VARCHAR
            )
        """)
        conn.executemany(
            "INSERT INTO t VALUES (?, ?, ?, ?)",
            [(1, "AFG", 1, None), (2, "AFG", 2, None)],
        )
        assign_new_codes(
            conn,
            "t",
            id_column="id_col",
            parent_column="parent_code",
            sort_columns=["sort_col"],
            code_column="code_col",
            fmt=_FMT,
            level=1,
            existing_codes=["AFG.001", "AFG.005"],
        )
        by_rank = dict(conn.execute("SELECT sort_col, code_col FROM t").fetchall())
    assert by_rank[1] == "AFG.006"
    assert by_rank[2] == "AFG.007"


def test_detect_code_format_infers_delimiter_root_and_mode_width():
    with duckdb.connect() as conn:
        conn.execute("CREATE TABLE t (code VARCHAR)")
        codes = ["AFG.001", "AFG.002", "AFG.003", "AFG.1000"]
        conn.executemany("INSERT INTO t VALUES (?)", [(c,) for c in codes])
        fmt = detect_code_format(conn, "t", "code")
    assert fmt.root_code == "AFG"
    assert fmt.delimiter == "."
    assert fmt.min_width == _MIN_WIDTH


def test_detect_code_format_raises_on_mixed_roots():
    with duckdb.connect() as conn:
        conn.execute("CREATE TABLE t (code VARCHAR)")
        conn.executemany("INSERT INTO t VALUES (?)", [("AFG.001",), ("PAK.001",)])
        with pytest.raises(ValueError, match="constant root"):
            detect_code_format(conn, "t", "code")


def test_detect_code_format_raises_when_no_delimiter_present():
    with duckdb.connect() as conn:
        conn.execute("CREATE TABLE t (code VARCHAR)")
        conn.executemany("INSERT INTO t VALUES (?)", [("AFG",), ("AFG",)])
        with pytest.raises(ValueError, match="single recurring delimiter"):
            detect_code_format(conn, "t", "code")


def test_detect_code_format_disputed_territory_root_is_opaque():
    """root_code is never shape-checked; a non-ISO3 prefix works identically."""
    with duckdb.connect() as conn:
        conn.execute("CREATE TABLE t (code VARCHAR)")
        conn.executemany("INSERT INTO t VALUES (?)", [("XKO.001",), ("XKO.002",)])
        fmt = detect_code_format(conn, "t", "code")
    assert fmt.root_code == "XKO"


@pytest.mark.parametrize(
    ("value", "expected"),
    [(3, 3), ("3", 3), ("2,2,4", (2, 2, 4)), ([2, 3], (2, 3)), ("AUTO", "auto")],
)
def test_parse_min_width_forms(value, expected):
    assert parse_min_width(value) == expected


@pytest.mark.parametrize("value", ["0", "2,x", "", [2, 0]])
def test_parse_min_width_rejects(value):
    with pytest.raises(ValueError, match="min_width"):
        parse_min_width(value)


def test_code_format_width_per_level_and_count_check():
    fmt = CodeFormat(root_code="AFG", delimiter=".", min_width=(2, 4))
    assert (fmt.width(1), fmt.width(2)) == (2, 4)
    assert CodeFormat("AFG", ".", "auto").width(1) is None
    with pytest.raises(ValueError, match="2 widths"):
        fmt.check_level_count(3)


def test_assign_new_codes_auto_width_fits_widest_tail_and_retained():
    with duckdb.connect() as conn:
        conn.execute(
            "CREATE TABLE t (id_col INTEGER, parent_code VARCHAR, code_col VARCHAR)"
        )
        rows = [(i, "AFG.01", None) for i in range(12)] + [(12, "AFG.02", None)]
        conn.executemany("INSERT INTO t VALUES (?, ?, ?)", rows)
        assign_new_codes(
            conn,
            "t",
            id_column="id_col",
            parent_column="parent_code",
            sort_columns=["id_col"],
            code_column="code_col",
            fmt=CodeFormat(root_code="AFG", delimiter=".", min_width="auto"),
            level=2,
            existing_codes=["AFG.02.001"],
        )
        codes = dict(conn.execute("SELECT id_col, code_col FROM t").fetchall())
    assert codes[0] == "AFG.01.001"
    assert codes[11] == "AFG.01.012"
    assert codes[12] == "AFG.02.002"


def test_detect_code_format_per_level_widths():
    with duckdb.connect() as conn:
        conn.execute("CREATE TABLE t (code VARCHAR)")
        codes = ["AFG.01.001", "AFG.01.002", "AFG.02.001"]
        conn.executemany("INSERT INTO t VALUES (?)", [(c,) for c in codes])
        assert detect_code_format(conn, "t", "code").min_width == (2, 3)


_UNDELIMITED = CodeFormat(root_code="BH", delimiter="", min_width=(2, 2, 4))
_AFTER_07 = 8


def test_parse_code_without_delimiter_splits_by_width():
    assert parse_code("BH51030366", _UNDELIMITED) == ["BH", "51", "03", "0366"]
    assert parent_prefix("BH51030366", _UNDELIMITED) == "BH5103"
    assert rewrite_child_code("BH5103", "BH52", _UNDELIMITED) == "BH5203"
    with pytest.raises(ValueError, match="split by width"):
        parse_code("BH510", _UNDELIMITED)


def test_next_available_integer_without_delimiter():
    existing = ["BH5101", "BH5107", "BH5201"]
    assert next_available_integer(existing, "BH51", _UNDELIMITED) == _AFTER_07


def test_detect_undelimited_format_per_level_widths():
    with duckdb.connect() as conn:
        conn.execute("CREATE TABLE t (c1 VARCHAR, c2 VARCHAR, c3 VARCHAR)")
        conn.executemany(
            "INSERT INTO t VALUES (?, ?, ?)",
            [("BH51", "BH5103", "BH51030366"), ("BH52", "BH5201", "BH52010101")],
        )
        assert not has_delimiter(conn, "t", "c3")
        fmt = detect_undelimited_format(conn, "t", {1: "c1", 2: "c2", 3: "c3"})
    assert fmt == _UNDELIMITED
