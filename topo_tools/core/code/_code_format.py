"""A hierarchical code's own delimiter/root/zero-pad configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CodeFormat:
    """One target format for a dot-style hierarchical code. No default values."""

    root_code: str
    delimiter: str
    min_width: int


def resolve_code_format(root_code: str, delimiter: str, min_width: int) -> CodeFormat:
    """Validate root_code/delimiter/min_width and build a CodeFormat."""
    if not root_code:
        msg = "root_code must be a non-empty string"
        raise ValueError(msg)
    if len(delimiter) != 1:
        msg = f"delimiter must be a single character, got {delimiter!r}"
        raise ValueError(msg)
    if min_width < 1:
        msg = f"min_width must be positive, got {min_width}"
        raise ValueError(msg)
    return CodeFormat(root_code=root_code, delimiter=delimiter, min_width=min_width)
