"""Derives a parent's next unused sequential integer from its live sibling codes."""

from topo_tools.core.code._code_format import CodeFormat


def used_integers(
    existing_codes: list[str], parent_code: str, fmt: CodeFormat
) -> set[int]:
    """Return the integers parent_code's own direct children already use."""
    prefix = f"{parent_code}{fmt.delimiter}"
    used: set[int] = set()
    for code in existing_codes:
        if not code.startswith(prefix):
            continue
        tail = code[len(prefix) :]
        if fmt.delimiter and fmt.delimiter in tail:
            continue
        try:
            used.add(int(tail))
        except ValueError:
            continue
    return used


def next_available_integer(
    existing_codes: list[str], parent_code: str, fmt: CodeFormat
) -> int:
    """Return parent_code's next unused integer among its own live direct children."""
    return max(used_integers(existing_codes, parent_code, fmt), default=0) + 1
