"""Pure string operations on a hierarchical code, given its own CodeFormat."""

from topo_tools.core.code._code_format import CodeFormat


def parse_code(code: str, fmt: CodeFormat) -> list[str]:
    """Split code into its delimiter-separated components, root first."""
    return code.split(fmt.delimiter)


def build_code(components: list[str], fmt: CodeFormat) -> str:
    """Join components with fmt's own delimiter."""
    return fmt.delimiter.join(components)


def parent_prefix(code: str, fmt: CodeFormat) -> str:
    """Return code with its own last component removed, i.e. its parent's code."""
    components = parse_code(code, fmt)
    if len(components) <= 1:
        msg = f"code {code!r} has no parent under format {fmt!r}"
        raise ValueError(msg)
    return build_code(components[:-1], fmt)


def last_component(code: str, fmt: CodeFormat) -> str:
    """Return code's own final, unpadded-string component."""
    return parse_code(code, fmt)[-1]
