"""Public API: dissolve a polygon layer into every detected coarser admin level."""

from logging import getLogger
from pathlib import Path

from duckdb import DuckDBPyConnection

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
from topo_tools.core.package_polygons import _01_inputs as inputs
from topo_tools.core.package_polygons import _02_dissolve as dissolve_stage
from topo_tools.core.package_polygons import _03_outputs as outputs
from topo_tools.core.package_polygons._03_outputs import LevelOutput
from topo_tools.core.schema_map._levels import detect_levels
from topo_tools.core.schema_map._target_schema import (
    DEFAULT_TARGET_SCHEMA_PATH,
    TargetSchema,
    load_target_schema,
)

logger = getLogger(__name__)

_STEP_ORDER = ["inputs", "dissolve", "outputs"]

_STEP_TABLES = {
    "inputs": ["{n}_01"],
    # "dissolve" is absent: per-level table names are dynamic ("{n}_02_{level}").
    "outputs": [],
}


def _resolve_level_dest(
    output_path: str | Path | None, input_path: Path | str, n: int
) -> Path:
    """Resolve one level's output path: {n}-templated, or the "_admin{n}" default."""
    if output_path is None:
        return default_output_path(input_path, f"_admin{n}")
    text = str(output_path)
    if "{n}" not in text:
        msg = f"output_path given without a literal '{{n}}' placeholder: {output_path}"
        raise ValueError(msg)
    return Path(text.format(n=n))


def _resolve_level_issues(issues_path: str | Path | None, dest: Path, n: int) -> Path:
    """Resolve one level's issues path: {n}-templated, or dest + "_issues"."""
    if issues_path is None:
        return dest.with_stem(dest.stem + "_issues")
    text = str(issues_path)
    if "{n}" not in text:
        msg = f"issues_path given without a literal '{{n}}' placeholder: {issues_path}"
        raise ValueError(msg)
    return Path(text.format(n=n))


def _load_plan(  # noqa: PLR0913, PLR0917
    conn: DuckDBPyConnection,
    name: str,
    input_path: Path | str,
    output_path: str | Path | None,
    issues_path: str | Path | None,
    target_schema_path: Path,
    *,
    overwrite: bool,
) -> tuple[TargetSchema, list[int], list[LevelOutput]]:
    """Load the target schema, detect levels, and resolve every level's plan."""
    schema = load_target_schema(target_schema_path)
    levels = detect_levels(conn, f"{name}_01", schema)
    plan = _plan_levels(
        name, input_path, output_path, issues_path, levels, overwrite=overwrite
    )
    return schema, levels, plan


def _plan_levels(  # noqa: PLR0913
    name: str,
    input_path: Path | str,
    output_path: str | Path | None,
    issues_path: str | Path | None,
    levels: list[int],
    *,
    overwrite: bool,
) -> list[LevelOutput]:
    """Resolve every level's output/issues paths, checking overwrite up front."""
    finest = max(levels)
    items = []
    for n in levels:
        dest = _resolve_level_dest(output_path, input_path, n)
        if n == finest and isinstance(input_path, Path) and dest == input_path:
            items.append(
                LevelOutput(level=n, table=f"{name}_01", dest=None, issues_dest=None)
            )
            continue

        issues_dest = _resolve_level_issues(issues_path, dest, n)
        check_overwrite(dest, overwrite=overwrite)
        check_overwrite(issues_dest, overwrite=overwrite)
        table = f"{name}_01" if n == finest else f"{name}_02_{n}"
        items.append(
            LevelOutput(level=n, table=table, dest=dest, issues_dest=issues_dest)
        )
    return items


def package_polygons(  # noqa: PLR0913
    input_path: str | Path,
    output_path: str | Path | None = None,
    issues_path: str | Path | None = None,
    target_schema_path: str | Path | None = None,
    *,
    threads: int | None = None,
    tmp_dir: str | Path | None = None,
    overwrite: bool = True,
    debug: bool = False,
    step: str | None = None,
) -> None:
    """Dissolve a polygon layer into every detected coarser admin level."""
    if step is not None and step not in _STEP_ORDER:
        msg = f"step must be one of {_STEP_ORDER}, got {step!r}"
        raise ValueError(msg)

    input_path = resolve_input_path(input_path)
    target_schema_path = (
        Path(target_schema_path)
        if target_schema_path is not None
        else DEFAULT_TARGET_SCHEMA_PATH
    )

    name = input_basename(input_path).replace(".", "_") + "_package_polygons"

    with (
        resolve_tmp_dir(tmp_dir, debug=debug) as tmp_dir_path,
        pipeline_connection(
            name, tmp_dir_path, threads=threads, debug=debug, step=step
        ) as conn,
    ):
        logger.info("starting: %s", name)
        plan: list[LevelOutput] | None = None
        for s in _STEP_ORDER:
            if step and step != s:
                continue
            if debug:
                logger.info("=== %s ===", s)
            if s == "inputs":
                inputs.main(conn, name, input_path)
            elif s == "dissolve":
                schema, levels, plan = _load_plan(
                    conn,
                    name,
                    input_path,
                    output_path,
                    issues_path,
                    target_schema_path,
                    overwrite=overwrite,
                )
                dissolve_stage.main(conn, name, levels, schema)
            elif s == "outputs":
                if plan is None:
                    _schema, _levels, plan = _load_plan(
                        conn,
                        name,
                        input_path,
                        output_path,
                        issues_path,
                        target_schema_path,
                        overwrite=overwrite,
                    )
                outputs.main(conn, name, plan, debug=debug)
        maybe_export_debug_tables(
            conn, tmp_dir_path, name, step, _STEP_TABLES, debug=debug
        )
        logger.info("done: %s", name)
