"""Unit tests for core/admin_columns.py's template-based column ordering."""

import pytest

from topo_tools.core.admin_columns import canonical_order, sibling_name


def test_orders_deepest_level_first_names_before_codes():
    columns = [
        "extra",
        "adm1_code",
        "adm3_name1",
        "adm2_code",
        "adm1_name",
        "adm3_code",
        "adm2_name1",
        "adm2_name",
        "adm3_name",
    ]
    ordered, sort_column = canonical_order(columns, "adm{n}_name", "adm{n}_code")
    assert ordered == [
        "adm3_name",
        "adm3_name1",
        "adm3_code",
        "adm2_name",
        "adm2_name1",
        "adm2_code",
        "adm1_name",
        "adm1_code",
        "extra",
    ]
    assert sort_column == "adm3_code"


def test_other_level_columns_sit_between_names_and_codes():
    columns = ["adm1_pcode", "adm1_ref_name1", "adm1_name", "adm0_pcode", "lang"]
    ordered, sort_column = canonical_order(columns, "adm{n}_name", "adm{n}_pcode")
    assert ordered == [
        "adm1_name",
        "adm1_ref_name1",
        "adm1_pcode",
        "adm0_pcode",
        "lang",
    ]
    assert sort_column == "adm1_pcode"


def test_template_with_trailing_level_number():
    columns = ["GID_1", "GID_21", "NAME_2_1", "GID_2", "NAME_21", "NAME_2", "NAME_1"]
    ordered, sort_column = canonical_order(columns, "NAME_{n}", "GID_{n}")
    assert ordered == [
        "NAME_21",
        "GID_21",
        "NAME_2",
        "NAME_2_1",
        "GID_2",
        "NAME_1",
        "GID_1",
    ]
    assert sort_column == "GID_21"


@pytest.mark.parametrize(
    ("column", "expected"),
    [("adm2_name", "adm2_name1"), ("GID_2", "GID_2_1"), ("pcode2", "pcode2_1")],
)
def test_sibling_name_separates_after_a_digit(column, expected):
    assert sibling_name(column, 1) == expected


def test_sorts_by_deepest_level_that_has_a_code():
    columns = ["adm3_name", "adm2_name", "adm2_code"]
    _, sort_column = canonical_order(columns, "adm{n}_name", "adm{n}_code")
    assert sort_column == "adm2_code"


def test_no_matching_columns_keeps_input_order():
    columns = ["b", "a", "c"]
    assert canonical_order(columns, "adm{n}_name", "adm{n}_code") == (columns, None)


def test_prefix_match_needs_a_known_level():
    columns = ["adm10x", "adm1_name", "adm1_code", "adm1_area"]
    ordered, _ = canonical_order(columns, "adm{n}_name", "adm{n}_code")
    assert ordered == ["adm1_name", "adm1_area", "adm1_code", "adm10x"]
