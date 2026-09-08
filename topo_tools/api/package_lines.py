"""Public API: a deduplicated shared+exterior admin boundary line network."""

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
from topo_tools.core.package_lines import _01_inputs as inputs
from topo_tools.core.package_lines import _02_boundaries as boundaries_stage
from topo_tools.core.package_lines import _03_outputs as outputs
from topo_tools.core.schema_map._levels import detect_levels
from topo_tools.core.schema_map._target_schema import (
    DEFAULT_TARGET_SCHEMA_PATH,
    load_target_schema,
)

logger = getLogger(__name__)

_STEP_ORDER = ["inputs", "boundaries", "outputs"]

_STEP_TABLES = {
    "inputs": ["{n}_01"],
    "boundaries": ["{n}_02"],
    "outputs": [],
}


def package_lines(  # noqa: PLR0913
    input_path: str | Path,
    output_path: str | Path | None = None,
    target_schema_path: str | Path | None = None,
    *,
    depth_column: str = "adm_lvl",
    threads: int | None = None,
    tmp_dir: str | Path | None = None,
    overwrite: bool = True,
    debug: bool = False,
    step: str | None = None,
) -> None:
    """Deduplicated shared+exterior boundary lines, classified by admin level."""
    if step is not None and step not in _STEP_ORDER:
        msg = f"step must be one of {_STEP_ORDER}, got {step!r}"
        raise ValueError(msg)

    input_path = resolve_input_path(input_path)
    output_path = (
        Path(output_path)
        if output_path is not None
        else default_output_path(input_path, "_lines")
    )
    check_overwrite(output_path, overwrite=overwrite)
    target_schema_path = (
        Path(target_schema_path)
        if target_schema_path is not None
        else DEFAULT_TARGET_SCHEMA_PATH
    )

    name = input_basename(input_path).replace(".", "_") + "_package_lines"

    with (
        resolve_tmp_dir(tmp_dir, debug=debug) as tmp_dir_path,
        pipeline_connection(
            name, tmp_dir_path, threads=threads, debug=debug, step=step
        ) as conn,
    ):
        logger.info("starting: %s", name)
        for s in _STEP_ORDER:
            if step and step != s:
                continue
            if debug:
                logger.info("=== %s ===", s)
            if s == "inputs":
                inputs.main(conn, name, input_path)
            elif s == "boundaries":
                schema = load_target_schema(target_schema_path)
                levels = detect_levels(conn, f"{name}_01", schema)
                boundaries_stage.main(conn, name, levels, schema, depth_column)
            elif s == "outputs":
                outputs.main(conn, name, output_path, debug=debug)
        maybe_export_debug_tables(
            conn, tmp_dir_path, name, step, _STEP_TABLES, debug=debug
        )
        logger.info("done: %s", name)
