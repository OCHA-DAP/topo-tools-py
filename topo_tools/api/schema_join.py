"""Public API: copy a parent layer's hierarchy columns onto each overlapping child."""

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
from topo_tools.core.schema_join import _01_inputs as inputs
from topo_tools.core.schema_join import _02_assign as assign_stage
from topo_tools.core.schema_join import _03_join as join_stage
from topo_tools.core.schema_join import _04_outputs as outputs
from topo_tools.core.schema_join._constants import MIN_OVERLAP_DEFAULT
from topo_tools.core.schema_map._target_schema import resolve_explicit_target_schema

logger = getLogger(__name__)

_STEP_ORDER = ["inputs", "assign", "join", "outputs"]

_STEP_TABLES = {
    "inputs": ["{n}_child_01", "{n}_parent_01"],
    "assign": ["{n}_02_assign", "{n}_02_pairs", "{n}_02_share"],
    "join": ["{n}_03", "{n}_03_mismatch"],
    "outputs": ["{n}_04"],
}


def join(  # noqa: PLR0913
    child_path: str | Path,
    parent_path: str | Path,
    output_path: str | Path | None = None,
    *,
    issues_path: str | Path | None = None,
    name_field: str | None = None,
    code_field: str | None = None,
    min_overlap: float = MIN_OVERLAP_DEFAULT,
    threads: int | None = None,
    tmp_dir: str | Path | None = None,
    overwrite: bool = True,
    debug: bool = False,
    step: str | None = None,
) -> None:
    """Copy each child's plurality-overlap parent's hierarchy columns onto it.

    Omitting name_field/code_field triggers structural auto-detection.
    """
    if step is not None and step not in _STEP_ORDER:
        msg = f"step must be one of {_STEP_ORDER}, got {step!r}"
        raise ValueError(msg)
    if not 0 < min_overlap <= 1:
        msg = f"min_overlap must be in (0, 1], got {min_overlap!r}"
        raise ValueError(msg)

    child_path = resolve_input_path(child_path)
    parent_path = resolve_input_path(parent_path)
    schema = resolve_explicit_target_schema(name_field, code_field)
    output_path = (
        Path(output_path)
        if output_path is not None
        else default_output_path(child_path, "_join")
    )
    issues_path = (
        Path(issues_path)
        if issues_path is not None
        else output_path.with_stem(output_path.stem + "_issues")
    )
    check_overwrite(output_path, overwrite=overwrite)
    check_overwrite(issues_path, overwrite=overwrite)

    name = input_basename(child_path).replace(".", "_") + "_schema_join"

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
                inputs.main(conn, name, child_path, parent_path)
            elif s == "assign":
                assign_stage.main(conn, name)
            elif s == "join":
                join_stage.main(conn, name, schema)
            elif s == "outputs":
                outputs.main(
                    conn,
                    name,
                    output_path,
                    issues_path,
                    min_overlap=min_overlap,
                    debug=debug,
                )
        maybe_export_debug_tables(
            conn, tmp_dir_path, name, step, _STEP_TABLES, debug=debug
        )
        logger.info("done: %s", name)
