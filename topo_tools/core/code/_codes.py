"""Pure string operations on a hierarchical code, given its own CodeFormat."""

from topo_tools.core.code._code_format import CodeFormat


def parse_code(code: str, fmt: CodeFormat) -> list[str]:
    """Split code into its components, root first; by width without a delimiter."""
    if fmt.delimiter:
        return code.split(fmt.delimiter)
    if not code.startswith(fmt.root_code):
        msg = f"code {code!r} does not start with root {fmt.root_code!r}"
        raise ValueError(msg)
    components, rest, level = [fmt.root_code], code[len(fmt.root_code) :], 1
    while rest:
        width = fmt.width(level)
        if width is None or len(rest) < width:
            msg = f"code {code!r} can't be split by width under format {fmt!r}"
            raise ValueError(msg)
        components.append(rest[:width])
        rest, level = rest[width:], level + 1
    return components


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
