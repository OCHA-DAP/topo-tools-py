"""Matches admin-hierarchy columns against `{n}`-templated field names, by name only."""

import re

DEFAULT_NAME_FIELD = "adm{n}_name"
DEFAULT_CODE_FIELD = "adm{n}_code"

_NAME, _OTHER, _CODE = 0, 1, 2


def sibling_name(column: str, index: int) -> str:
    """Name column's index-th numbered sibling, `_`-separated after a trailing digit."""
    return f"{column}_{index}" if column[-1:].isdigit() else f"{column}{index}"


def field_prefix(template: str) -> str:
    """Return a `{n}`-templated field's prefix, e.g. "adm" from "adm{n}_pcode"."""
    return template.split("{n}", maxsplit=1)[0]


def column_families(
    columns: list[str], levels: list[int], prefix: str
) -> dict[str, dict[int, str]]:
    """Group level columns by suffix, e.g. {"_pcode": {1: "adm1_pcode", ...}}."""
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)(.*)$")
    families: dict[str, dict[int, str]] = {}
    for column in columns:
        match = pattern.match(column)
        if not match:
            continue
        level, suffix = int(match.group(1)), match.group(2)
        if level not in levels:
            continue
        families.setdefault(suffix, {})[level] = column
    return families


def template_families(
    columns: list[str], levels: list[int], name_field: str, code_field: str
) -> dict[str, dict[int, str]]:
    """Group level columns under both templates' prefixes, keyed like "adm{n}_name"."""
    families: dict[str, dict[int, str]] = {}
    for prefix in dict.fromkeys([field_prefix(code_field), field_prefix(name_field)]):
        for suffix, per_level in column_families(columns, levels, prefix).items():
            families[f"{prefix}{{n}}{suffix}"] = per_level
    return families


def _family_pattern(template: str) -> re.Pattern:
    """Match a template's own column and its siblings (`adm2_name1`, `GID_2_1`)."""
    before, _, after = template.partition("{n}")
    sep = "_" if not after or after[-1].isdigit() else ""
    return re.compile(rf"^{re.escape(before)}(\d+){re.escape(after)}(?:{sep}(\d+))?$")


def canonical_order(
    columns: list[str], name_field: str, code_field: str
) -> tuple[list[str], str | None]:
    """Order columns deepest level first (names, other, codes), then the rest.

    Also returns the deepest level's own code column to sort rows by, if any.
    """
    name_re, code_re = _family_pattern(name_field), _family_pattern(code_field)
    prefix = field_prefix(code_field)
    level_re = re.compile(rf"^{re.escape(prefix)}(\d+)(?!\d)") if prefix else None
    keys: dict[str, tuple[int, int, int]] = {}
    for column in columns:
        if match := code_re.match(column):
            keys[column] = (int(match[1]), _CODE, int(match[2] or 0))
        elif match := name_re.match(column):
            keys[column] = (int(match[1]), _NAME, int(match[2] or 0))
    levels = {level for level, _, _ in keys.values()}
    for position, column in enumerate(columns):
        if column in keys or not level_re or not (match := level_re.match(column)):
            continue
        if int(match[1]) in levels:
            keys[column] = (int(match[1]), _OTHER, position)
    ordered = sorted(keys, key=lambda c: (-keys[c][0], keys[c][1], keys[c][2]))
    codes = {
        level: column
        for column, (level, _, _) in keys.items()
        if column == code_field.format(n=level)
    }
    sort_column = codes[max(codes)] if codes else None
    return ordered + [c for c in columns if c not in keys], sort_column
