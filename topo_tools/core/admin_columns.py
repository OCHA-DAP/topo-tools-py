"""Matches admin-hierarchy columns against `{n}`-templated field names, by name only."""

import re

DEFAULT_NAME_FIELD = "adm{n}_name"
DEFAULT_CODE_FIELD = "adm{n}_code"

_NAME, _OTHER, _CODE = 0, 1, 2


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


def _family_pattern(template: str) -> re.Pattern:
    """Match a template's own column and its numbered siblings (`adm2_name1`)."""
    before, _, after = template.partition("{n}")
    return re.compile(rf"^{re.escape(before)}(\d+){re.escape(after)}(\d*)$")


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
    for position, column in enumerate(columns):
        if match := code_re.match(column):
            keys[column] = (int(match[1]), _CODE, int(match[2] or 0))
        elif match := name_re.match(column):
            keys[column] = (int(match[1]), _NAME, int(match[2] or 0))
        elif level_re and (match := level_re.match(column)):
            keys[column] = (int(match[1]), _OTHER, position)
    ordered = sorted(keys, key=lambda c: (-keys[c][0], keys[c][1], keys[c][2]))
    codes = {
        level: column
        for column, (level, _, _) in keys.items()
        if column == code_field.format(n=level)
    }
    sort_column = codes[max(codes)] if codes else None
    return ordered + [c for c in columns if c not in keys], sort_column
