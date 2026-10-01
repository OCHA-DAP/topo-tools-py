"""Public API: assign each input feature to an overlay feature, then clip it to it."""

from logging import getLogger
from pathlib import Path

from topo_tools.core.assign import assign_one, load_input, load_original, load_overlay
from topo_tools.core.duckdb_utils import (
    maybe_export_debug_tables,
    pipeline_connection,
    resolve_tmp_dir,
)
from topo_tools.core.edge_clip import _01_clip as clip_stage
from topo_tools.core.edge_clip import _02_outputs as outputs
from topo_tools.core.io import (
    check_overwrite,
    default_output_path,
    input_basename,
    resolve_input_path,
)

logger = getLogger(__name__)

_STEP_ORDER = ["inputs", "assign", "clip", "outputs"]

_STEP_TABLES = {
    "inputs": ["{n}_input_01", "{n}_overlay_01", "{n}_original_01"],
    "assign": ["{n}_02_pairs", "{n}_02_assign", "{n}_02_unassigned"],
    "clip": ["{n}_03", "{n}_03_dropped", "{n}_03_detached"],
    "outputs": [],
}


def clip(  # noqa: C901, PLR0912, PLR0913
    input_path: str | Path,
    overlay_path: str | Path,
    output_path: str | Path | None = None,
    issues_path: str | Path | None = None,
    *,
    name: str | None = None,
    threads: int | None = None,
    tmp_dir: str | Path | None = None,
    overwrite: bool = True,
    debug: bool = False,
    step: str | None = None,
    match_column: str | None = None,
    overlay_match_column: str | None = None,
    input_match_column: str | None = None,
    carry_columns: list[str] | None = None,
    original_path: str | Path | None = None,
) -> None:
    """Assign one input file to its overlay feature via assign-one, then clip it."""
    if match_column is not None and (overlay_match_column or input_match_column):
        msg = (
            "match_column is mutually exclusive with overlay feature/input_match_column"
        )
        raise ValueError(msg)
    if bool(overlay_match_column) != bool(input_match_column):
        msg = "overlay_match_column and input_match_column must be given together"
        raise ValueError(msg)
    if match_column is not None:
        overlay_match_column = input_match_column = match_column
    code_join = bool(overlay_match_column and input_match_column)

    if step is not None and step not in _STEP_ORDER:
        msg = f"step must be one of {_STEP_ORDER}, got {step!r}"
        raise ValueError(msg)

    input_path = resolve_input_path(input_path)
    overlay_path = resolve_input_path(overlay_path)
    if original_path is not None:
        original_path = resolve_input_path(original_path)

    output_path = (
        Path(output_path)
        if output_path is not None
        else default_output_path(input_path, "_clipped")
    )
    resolved_issues_path = (
        Path(issues_path)
        if issues_path is not None
        else output_path.with_stem(output_path.stem + "_issues")
    )

    if name is None:
        name = input_basename(input_path).replace(".", "_") + "_edge_clip"

    if step in (None, "outputs"):
        check_overwrite(output_path, overwrite=overwrite)
        check_overwrite(resolved_issues_path, overwrite=overwrite)

    dest_by_source = {str(input_path): output_path}
    issues_dest_by_source = {str(input_path): resolved_issues_path}

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
                load_input(conn, name, [input_path])
                load_overlay(conn, name, overlay_path)
                if original_path is not None:
                    load_original(conn, name, [original_path])
            elif s == "assign":
                assign_one(
                    conn,
                    name,
                    overlay_match_column=overlay_match_column,
                    input_match_column=input_match_column,
                    carry_columns=carry_columns,
                )
            elif s == "clip":
                clip_stage.main(
                    conn,
                    name,
                    tmp_dir_path,
                    threads=threads,
                    debug=debug,
                    carry_columns=carry_columns,
                    original_table=(
                        f"{name}_original_01" if original_path is not None else None
                    ),
                )
            elif s == "outputs":
                outputs.main(
                    conn,
                    name,
                    dest_by_source,
                    issues_dest_by_source,
                    code_join=code_join,
                    debug=debug,
                )
        maybe_export_debug_tables(
            conn, tmp_dir_path, name, step, _STEP_TABLES, debug=debug
        )
        logger.info("done: %s", name)
