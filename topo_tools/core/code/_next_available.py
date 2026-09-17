"""Derives a parent's next unused sequential integer from its live sibling codes."""

from topo_tools.core.code._code_format import CodeFormat


def next_available_integer(
    existing_codes: list[str], parent_code: str, fmt: CodeFormat
) -> int:
    """Return parent_code's next unused integer among its own live direct children."""
    prefix = f"{parent_code}{fmt.delimiter}"
    max_n = 0
    for code in existing_codes:
        if not code.startswith(prefix):
            continue
        tail = code[len(prefix) :]
        if fmt.delimiter in tail:
            continue
        try:
            n = int(tail)
        except ValueError:
            continue
        max_n = max(max_n, n)
    return max_n + 1
