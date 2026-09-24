"""Unit tests for core/admin_columns.py's template-based column ordering."""

from topo_tools.core.admin_columns import canonical_order


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
    columns = ["code_adm1", "code_adm10", "name_adm10", "name_adm1"]
    ordered, sort_column = canonical_order(columns, "name_adm{n}", "code_adm{n}")
    assert ordered == ["name_adm10", "code_adm10", "name_adm1", "code_adm1"]
    assert sort_column == "code_adm10"


def test_sorts_by_deepest_level_that_has_a_code():
    columns = ["adm3_name", "adm2_name", "adm2_code"]
    _, sort_column = canonical_order(columns, "adm{n}_name", "adm{n}_code")
    assert sort_column == "adm2_code"


def test_no_matching_columns_keeps_input_order():
    columns = ["b", "a", "c"]
    assert canonical_order(columns, "adm{n}_name", "adm{n}_code") == (columns, None)
