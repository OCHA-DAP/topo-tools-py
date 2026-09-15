"""Rebuilds a child's own code under a new parent prefix, tail untouched."""

from topo_tools.core.code._code_format import CodeFormat
from topo_tools.core.code._codes import last_component


def rewrite_child_code(old_code: str, new_parent_code: str, fmt: CodeFormat) -> str:
    """Reattach old_code's own tail component onto new_parent_code."""
    return f"{new_parent_code}{fmt.delimiter}{last_component(old_code, fmt)}"
