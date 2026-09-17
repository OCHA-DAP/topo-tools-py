"""Shared hierarchical-code primitive: format, detection, cascade, rewrite."""

from topo_tools.core.code._cascade import assign_new_codes
from topo_tools.core.code._code_format import CodeFormat, resolve_code_format
from topo_tools.core.code._codes import (
    build_code,
    last_component,
    parent_prefix,
    parse_code,
)
from topo_tools.core.code._constants import TABLE_COPY_OPTS
from topo_tools.core.code._detect_format import detect_code_format
from topo_tools.core.code._next_available import next_available_integer
from topo_tools.core.code._rewrite import rewrite_child_code

__all__ = [
    "TABLE_COPY_OPTS",
    "CodeFormat",
    "assign_new_codes",
    "build_code",
    "detect_code_format",
    "last_component",
    "next_available_integer",
    "parent_prefix",
    "parse_code",
    "resolve_code_format",
    "rewrite_child_code",
]
