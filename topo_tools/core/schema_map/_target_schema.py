"""Output naming templates for a discovered hierarchy level `n`."""

from dataclasses import dataclass

from topo_tools.core.admin_columns import DEFAULT_CODE_FIELD, DEFAULT_NAME_FIELD


@dataclass(frozen=True)
class TargetSchema:
    """Output naming templates for a discovered hierarchy level `n`."""

    name_field: str
    code_field: str


DEFAULT_TARGET_SCHEMA = TargetSchema(
    name_field=DEFAULT_NAME_FIELD, code_field=DEFAULT_CODE_FIELD
)


def _require_placeholder(name_field: str, code_field: str, context: str) -> None:
    if "{n}" not in name_field or "{n}" not in code_field:
        msg = (
            f"name_field/code_field must both contain a '{{n}}' placeholder: {context}"
        )
        raise ValueError(msg)


def target_schema_from_fields(name_field: str, code_field: str) -> TargetSchema:
    """Build a TargetSchema from inline templates instead of a YAML file."""
    _require_placeholder(name_field, code_field, f"{name_field!r}/{code_field!r}")
    return TargetSchema(name_field=name_field, code_field=code_field)


def resolve_explicit_target_schema(
    name_field: str | None,
    code_field: str | None,
) -> TargetSchema | None:
    """Resolve an explicit schema, or None to trigger structural auto-detection.

    Raises ValueError if only one of name_field/code_field is given.
    """
    if (name_field is None) != (code_field is None):
        msg = "name_field and code_field must be given together"
        raise ValueError(msg)
    if name_field is not None and code_field is not None:
        return target_schema_from_fields(name_field, code_field)
    return None
