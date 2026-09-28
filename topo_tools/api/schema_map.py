"""Public API: map a crosswalk and/or apply it to rename/drop columns."""

from logging import getLogger
from pathlib import Path

from topo_tools.core.duckdb_utils import (
    maybe_export_debug_tables,
    pipeline_connection,
    resolve_tmp_dir,
)
from topo_tools.core.io import (
    check_overwrite,
    default_output_path,
    input_basename,
    resolve_input_path,
)
from topo_tools.core.schema_crosswalk import _03_apply as apply_stage
from topo_tools.core.schema_crosswalk import _04_outputs as outputs
from topo_tools.core.schema_map import _01_inputs as inputs
from topo_tools.core.schema_map import _02_map as map_stage
from topo_tools.core.schema_map._target_schema import (
    DEFAULT_TARGET_SCHEMA,
    resolve_explicit_target_schema,
)

logger = getLogger(__name__)

_STEP_ORDER = ["inputs", "map", "apply", "outputs"]

_STEP_TABLES = {
    "inputs": ["{n}_01"],
    "map": ["{n}_02"],
    "apply": ["{n}_apply_02", "{n}_apply_crosswalk"],
    "outputs": [],
}


def _validate_mode(  # noqa: PLR0913
    output_path: str | Path | None,
    csv_input: str | Path | None,
    csv_output: str | Path | None,
    *,
    map_only: bool,
    level: int | None,
    step: str | None,
) -> list[str]:
    """Raise ValueError on conflicting mode arguments; return the stages to run."""
    conflicts = [
        (csv_input is not None and map_only, "csv_input and map_only"),
        (
            csv_input is not None and csv_output is not None,
            "csv_input and csv_output",
        ),
        (
            csv_input is not None and level is not None,
            "csv_input and level",
        ),
        (map_only and output_path is not None, "map_only and output_path"),
    ]
    for conflict, label in conflicts:
        if conflict:
            msg = f"{label} can't be given together"
            raise ValueError(msg)
    if output_path is not None and Path(output_path).suffix.lower() == ".csv":
        msg = (
            f"output_path {output_path} is a CSV; the mapped layer keeps the "
            "input's format (pass csv_output/--csv-output for the "
            "crosswalk CSV)"
        )
        raise ValueError(msg)

    skipped = "map" if csv_input is not None else "apply" if map_only else None
    stages = [s for s in _STEP_ORDER if s != skipped]
    if step is not None and step not in stages:
        msg = f"step must be one of {stages}, got {step!r}"
        raise ValueError(msg)
    return stages


def _resolve_outputs(
    input_path: Path | str,
    output_path: str | Path | None,
    csv_output: str | Path | None,
    csv_input: Path | None,
    *,
    map_only: bool,
) -> tuple[Path | None, Path | None]:
    """Return the (mapped layer, crosswalk CSV) paths this mode writes, else None."""
    if map_only:
        layer_path = None
    elif output_path is None:
        layer_path = default_output_path(input_path, "_mapped")
    else:
        layer_path = Path(output_path)
    if csv_input is not None:
        csv_path = None
    elif csv_output is None:
        csv_path = default_output_path(input_path, "_crosswalk").with_suffix(".csv")
    else:
        csv_path = Path(csv_output)
    return layer_path, csv_path


def map(  # noqa: A001, PLR0913
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    csv_input: str | Path | None = None,
    csv_output: str | Path | None = None,
    map_only: bool = False,
    name_field: str | None = None,
    code_field: str | None = None,
    level: int | None = None,
    layer: str | None = None,
    threads: int | None = None,
    tmp_dir: str | Path | None = None,
    overwrite: bool = True,
    debug: bool = False,
    step: str | None = None,
) -> None:
    """Map a crosswalk and apply it, apply an edited crosswalk, or only map.

    Processes exactly one file per call.
    """
    stages = _validate_mode(
        output_path,
        csv_input,
        csv_output,
        map_only=map_only,
        level=level,
        step=step,
    )

    input_path = resolve_input_path(input_path)
    schema = resolve_explicit_target_schema(name_field, code_field) or (
        DEFAULT_TARGET_SCHEMA
    )
    csv_input = Path(csv_input) if csv_input is not None else None
    output_path, csv_output = _resolve_outputs(
        input_path, output_path, csv_output, csv_input, map_only=map_only
    )
    for path in (output_path, csv_output):
        if path is not None:
            check_overwrite(path, overwrite=overwrite)

    name = input_basename(input_path).replace(".", "_") + "_schema_map"

    with (
        resolve_tmp_dir(tmp_dir, debug=debug) as tmp_dir_path,
        pipeline_connection(
            name, tmp_dir_path, threads=threads, debug=debug, step=step
        ) as conn,
    ):
        logger.info("starting: %s", name)
        for s in stages:
            if step and step != s:
                continue
            if debug:
                logger.info("=== %s ===", s)
            if s == "inputs":
                inputs.main(conn, name, input_path, layer)
            elif s == "map":
                map_stage.main(conn, name, schema, level)
            elif s == "apply":
                apply_stage.main(conn, name, input_path, schema, csv_input)
            elif s == "outputs":
                outputs.main(conn, name, csv_output, output_path, debug=debug)
        maybe_export_debug_tables(
            conn, tmp_dir_path, name, step, _STEP_TABLES, debug=debug
        )
        logger.info("done: %s", name)
