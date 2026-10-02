"""topo-tools CLI: click entry point."""

import glob
from logging import INFO, basicConfig, getLogger
from pathlib import Path

import click

from topo_tools.api import change as _change
from topo_tools.api import edge_clip as _edge_clip
from topo_tools.api import edge_extend as _edge_extend
from topo_tools.api import edge_match as _edge_match
from topo_tools.api import edge_mosaic as _edge_mosaic
from topo_tools.api import edge_stitch as _edge_stitch
from topo_tools.api import package as _package
from topo_tools.api import schema_fill as _schema_fill
from topo_tools.api import schema_join as _schema_join
from topo_tools.api import schema_map as _schema_map
from topo_tools.api import topo_clean as _topo_clean
from topo_tools.api import topo_detect as _topo_detect
from topo_tools.api.code_create import code_create as _code_create
from topo_tools.api.code_update import code_update as _code_update
from topo_tools.api.package_lines import package_lines as _package_lines
from topo_tools.api.package_points import package_points as _package_points
from topo_tools.api.package_polygons import package_polygons as _package_polygons
from topo_tools.core.change._constants import TAU_MATCH_DEFAULT, TAU_SAME_DEFAULT
from topo_tools.core.schema_join._constants import MIN_OVERLAP_DEFAULT

basicConfig(level=INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = getLogger(__name__)


def _split_commas(values: tuple[str, ...]) -> list[str]:
    """Flatten repeated --flag occurrences, each optionally comma-separated."""
    return [v for raw in values for v in raw.split(",")]


def _split_columns(value: str | None) -> list[str] | None:
    """Comma-split a column-list flag's raw value, or None if unset."""
    return value.split(",") if value is not None else None


def _parse_aggregations(values: tuple[str, ...]) -> dict[str, str] | None:
    """Parse repeated --aggregation 'column=function' values into a dict."""
    if not values:
        return None
    aggregations = {}
    for raw in values:
        column, sep, function = raw.partition("=")
        if not sep:
            msg = f"--aggregation must be 'column=function', got {raw!r}"
            raise click.BadParameter(msg)
        aggregations[column] = function
    return aggregations


_MERGE_OPTIONS = (
    click.option(
        "--merge",
        envvar="MERGE",
        is_flag=True,
        help=(
            "Carry overlay columns onto every matched input feature and keep "
            "an unmatched overlay or input feature unclipped in the output instead of "
            "dropping it. Narrow the carried columns with "
            "--overlay-include/--overlay-exclude/--input-include/"
            "--input-exclude; resolve a real name collision automatically "
            "with --prefer."
        ),
    ),
    click.option(
        "--overlay-include",
        envvar="OVERLAY_INCLUDE",
        default=None,
        help="Comma-separated overlay columns to carry (requires --merge).",
    ),
    click.option(
        "--overlay-exclude",
        envvar="OVERLAY_EXCLUDE",
        default=None,
        help="Comma-separated overlay columns to omit (requires --merge).",
    ),
    click.option(
        "--input-include",
        envvar="INPUT_INCLUDE",
        default=None,
        help="Comma-separated input columns to keep (requires --merge).",
    ),
    click.option(
        "--input-exclude",
        envvar="INPUT_EXCLUDE",
        default=None,
        help="Comma-separated input columns to drop (requires --merge).",
    ),
    click.option(
        "--prefer",
        envvar="PREFER",
        type=click.Choice(["overlay", "input"]),
        default=None,
        help=(
            "Resolve a real overlay/input column-name collision by keeping "
            "this side's column (requires --merge; mutually exclusive with "
            "the --overlay-*/--input-* narrowing flags)."
        ),
    ),
)


def _add_merge_options(f):  # noqa: ANN001, ANN202
    """Apply the shared --merge option set to a command function."""
    for option in reversed(_MERGE_OPTIONS):
        f = option(f)
    return f


_FILL_OPTIONS = (
    click.option(
        "--fill-schema",
        envvar="FILL_SCHEMA",
        is_flag=True,
        help=(
            "Cascade admin-hierarchy columns down and stamp each row's real "
            "depth, right before export. Narrow the target schema with "
            "--name-field/--code-field; rename the stamped depth column "
            "with --depth-column."
        ),
    ),
    click.option(
        "--name-field",
        envvar="NAME_FIELD",
        default=None,
        help="Name-field template, e.g. 'adm{n}_name' (requires --fill-schema "
        "and --code-field; default: structural auto-detection).",
    ),
    click.option(
        "--code-field",
        envvar="CODE_FIELD",
        default=None,
        help="Code-field template, e.g. 'adm{n}_code' (requires --fill-schema "
        "and --name-field; default: structural auto-detection).",
    ),
    click.option(
        "--depth-column",
        envvar="DEPTH_COLUMN",
        default="adm_lvl",
        show_default=True,
        help="Name of the new column stamping each row's real depth "
        "(requires --fill-schema).",
    ),
)


def _add_fill_options(f):  # noqa: ANN001, ANN202
    """Apply the shared --fill-schema option set to a command function."""
    for option in reversed(_FILL_OPTIONS):
        f = option(f)
    return f


@click.group()
@click.version_option(package_name="topo-tools", prog_name="topo-tools")
def cli() -> None:
    """topo-tools: DuckDB-powered geospatial topology utilities."""


@cli.command(name="edge-extend")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "lines", "attempt", "merge", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
def edge_extend(  # noqa: PLR0913, PLR0917
    input_file: str,
    output_file: str | None,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
) -> None:
    """Extend polygon boundaries outward with Voronoi diagrams to fill coverage gaps.

    OUTPUT_FILE defaults to INPUT_FILE with an "_extended" suffix if omitted.

    \b
    Examples:
      # Basic run, output name chosen automatically
      topo-tools edge-extend example.geojson

    \b
      # Explicit output
      topo-tools edge-extend example.gpkg example_extended.gpkg

    \b
      # Error instead of silently overwriting an existing output
      topo-tools edge-extend example.parquet example_extended.parquet --overwrite=false
    """
    logger.info("--debug=%s", debug)
    try:
        _edge_extend(
            input_file,
            Path(output_file) if output_file is not None else None,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
        )
    except (FileExistsError, RuntimeError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="topo-detect")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "issues", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
def topo_detect(  # noqa: PLR0913, PLR0917
    input_file: str,
    output_file: str | None,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
) -> None:
    """Scan a single polygon layer for gap/overlap coverage defects.

    OUTPUT_FILE defaults to INPUT_FILE with an "_issues" suffix if omitted.

    \b
    Examples:
      # Basic run, output name chosen automatically
      topo-tools topo-detect example.geojson

    \b
      # Explicit output
      topo-tools topo-detect example.gpkg example_issues.gpkg
    """
    logger.info("--debug=%s", debug)
    try:
        _topo_detect(
            input_file,
            Path(output_file) if output_file is not None else None,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
        )
    except (FileExistsError, RuntimeError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="package-polygons")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--issues-file",
    envvar="ISSUES_FILE",
    default=None,
    help="Issues report path template. Defaults to each level's own output "
    'with an "_issues" suffix.',
)
@click.option(
    "--name-field",
    envvar="NAME_FIELD",
    default=None,
    help="Name-field template, e.g. 'adm{n}_name' (requires --code-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--code-field",
    envvar="CODE_FIELD",
    default=None,
    help="Code-field template, e.g. 'adm{n}_code' (requires --name-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--output-name-field",
    envvar="OUTPUT_NAME_FIELD",
    default=None,
    help="Rename --name-field's columns to this template in every written level, "
    "e.g. 'adm{n}_label' (requires --name-field/--code-field).",
)
@click.option(
    "--output-code-field",
    envvar="OUTPUT_CODE_FIELD",
    default=None,
    help="Rename --code-field's columns to this template in every written level, "
    "e.g. 'adm{n}_pcode' (requires --name-field/--code-field).",
)
@click.option(
    "--aggregation",
    "aggregations",
    envvar="AGGREGATIONS",
    multiple=True,
    help="'column=function' override for a column that varies within a group "
    "(function is one of sum, min, max, avg, first; default: sum if numeric, "
    "else dropped) [may be repeated].",
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "dissolve", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
def package_polygons(  # noqa: PLR0913, PLR0917
    input_file: str,
    output_file: str | None,
    issues_file: str | None,
    name_field: str | None,
    code_field: str | None,
    output_name_field: str | None,
    output_code_field: str | None,
    aggregations: tuple[str, ...],
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
) -> None:
    """Dissolve a polygon layer into every detected coarser admin level.

    OUTPUT_FILE, if given, MUST contain a literal "{n}" placeholder, formatted
    per level; if omitted, each level defaults to INPUT_FILE with an
    "_admin{n}" suffix. The finest detected level is skipped when its
    computed path resolves to INPUT_FILE itself.

    \b
    Examples:
      # Default naming: input_admin1.geojson, input_admin2.geojson, ...
      topo-tools package-polygons admin3.geojson

    \b
      # Explicit {n} template
      topo-tools package-polygons admin3.geojson "level_{n}.geojson" \\
        --name-field adm{n}_name --code-field adm{n}_pcode
    """
    logger.info("--debug=%s", debug)
    try:
        _package_polygons(
            input_file,
            output_file,
            issues_file,
            name_field=name_field,
            code_field=code_field,
            output_name_field=output_name_field,
            output_code_field=output_code_field,
            aggregations=_parse_aggregations(aggregations),
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
        )
    except (FileExistsError, RuntimeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="package-points")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--name-field",
    envvar="NAME_FIELD",
    default=None,
    help="Name-field template, e.g. 'adm{n}_name' (requires --code-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--code-field",
    envvar="CODE_FIELD",
    default=None,
    help="Code-field template, e.g. 'adm{n}_code' (requires --name-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--depth-column",
    envvar="DEPTH_COLUMN",
    default="adm_lvl",
    show_default=True,
    help="Column name stamped with each point's own admin level.",
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "points", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
def package_points(  # noqa: PLR0913, PLR0917
    input_file: str,
    output_file: str | None,
    name_field: str | None,
    code_field: str | None,
    depth_column: str,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
) -> None:
    """One pole-of-inaccessibility label point per admin unit, every level combined.

    OUTPUT_FILE defaults to INPUT_FILE with a "_points" suffix if omitted.

    \b
    Examples:
      topo-tools package-points admin3.geojson
    """
    logger.info("--debug=%s", debug)
    try:
        _package_points(
            input_file,
            Path(output_file) if output_file is not None else None,
            name_field,
            code_field,
            depth_column=depth_column,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
        )
    except (FileExistsError, RuntimeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="package-lines")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--name-field",
    envvar="NAME_FIELD",
    default=None,
    help="Name-field template, e.g. 'adm{n}_name' (requires --code-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--code-field",
    envvar="CODE_FIELD",
    default=None,
    help="Code-field template, e.g. 'adm{n}_code' (requires --name-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--depth-column",
    envvar="DEPTH_COLUMN",
    default="adm_lvl",
    show_default=True,
    help="Column name stamped with each boundary's own coarsest admin level.",
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "boundaries", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
def package_lines(  # noqa: PLR0913, PLR0917
    input_file: str,
    output_file: str | None,
    name_field: str | None,
    code_field: str | None,
    depth_column: str,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
) -> None:
    """Deduplicated shared+exterior boundary lines, classified by admin level.

    OUTPUT_FILE defaults to INPUT_FILE with a "_lines" suffix if omitted.

    \b
    Examples:
      topo-tools package-lines admin3.geojson
    """
    logger.info("--debug=%s", debug)
    try:
        _package_lines(
            input_file,
            Path(output_file) if output_file is not None else None,
            name_field,
            code_field,
            depth_column=depth_column,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
        )
    except (FileExistsError, RuntimeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


@cli.command()
@click.argument("input_file", envvar="INPUT_FILE")
@click.option(
    "--output",
    "output",
    envvar="OUTPUT",
    default=None,
    help='Output path template containing a literal "{x}" placeholder, '
    'substituted per sub-tool ("admin{n}"/"points"/"lines"). Omit for defaults.',
)
@click.option(
    "--name-field",
    envvar="NAME_FIELD",
    default=None,
    help="Name-field template, e.g. 'adm{n}_name' (requires --code-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--code-field",
    envvar="CODE_FIELD",
    default=None,
    help="Code-field template, e.g. 'adm{n}_code' (requires --name-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--output-name-field",
    envvar="OUTPUT_NAME_FIELD",
    default=None,
    help="Rename --name-field's columns to this template in every written level, "
    "e.g. 'adm{n}_label' (requires --name-field/--code-field).",
)
@click.option(
    "--output-code-field",
    envvar="OUTPUT_CODE_FIELD",
    default=None,
    help="Rename --code-field's columns to this template in every written level, "
    "e.g. 'adm{n}_pcode' (requires --name-field/--code-field).",
)
@click.option(
    "--aggregation",
    "aggregations",
    envvar="AGGREGATIONS",
    multiple=True,
    help="'column=function' override for package-polygons, for a column that "
    "varies within a group (function is one of sum, min, max, avg, first; "
    "default: sum if numeric, else dropped) [may be repeated].",
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
def package(  # noqa: PLR0913, PLR0917
    input_file: str,
    output: str | None,
    name_field: str | None,
    code_field: str | None,
    output_name_field: str | None,
    output_code_field: str | None,
    aggregations: tuple[str, ...],
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
) -> None:
    """Run package-polygons, package-points, and package-lines against one input.

    \b
    Examples:
      # Defaults for all three outputs
      topo-tools package admin3.geojson

    \b
      # Explicit {x} template
      topo-tools package admin3.geojson --output "web/{x}.geojson"
    """
    logger.info("--debug=%s", debug)
    try:
        _package(
            input_file,
            output,
            name_field,
            code_field,
            output_name_field=output_name_field,
            output_code_field=output_code_field,
            aggregations=_parse_aggregations(aggregations),
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
        )
    except (FileExistsError, RuntimeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="topo-clean")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--issues-file",
    envvar="ISSUES_FILE",
    default=None,
    help='Issues report path. Defaults to OUTPUT_FILE with an "_issues" suffix.',
)
@click.option(
    "--maximum-gap-width",
    envvar="MAXIMUM_GAP_WIDTH",
    type=str,
    default=None,
    help="'thin' (fill thin/sliver-shaped gaps regardless of width), 'all' "
    "(fill every detected gap), or a number in decimal degrees (the layer's "
    "EPSG:4326 units, matches GDAL/OGR convention, not meters). Omit to fill "
    "only floating-point-noise-scale gaps (the default).",
)
@click.option(
    "--snapping-distance",
    envvar="SNAPPING_DISTANCE",
    type=str,
    default=None,
    help="A number in decimal degrees. Omit to snap at SNAP_TOLERANCE (the "
    "default). Noding robustness knob only.",
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "issues", "clean", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
def topo_clean(  # noqa: PLR0913, PLR0917
    input_file: str,
    output_file: str | None,
    issues_file: str | None,
    maximum_gap_width: str | None,
    snapping_distance: str | None,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
) -> None:
    """Detect and fix gap/overlap defects in a single polygon layer.

    OUTPUT_FILE defaults to INPUT_FILE with a "_cleaned" suffix if omitted.

    \b
    Examples:
      # Basic run: fills only floating-point-noise-scale gaps (the default)
      topo-tools topo-clean example.geojson

    \b
      # Fill thin/sliver-shaped gaps regardless of width
      topo-tools topo-clean example.gpkg --maximum-gap-width thin

    \b
      # Fill every detected gap, not just slivers
      topo-tools topo-clean example.gpkg --maximum-gap-width all

    \b
      # Cap gap-filling at ~0.0001 degrees (~11m at the equator)
      topo-tools topo-clean example.parquet --maximum-gap-width 0.0001
    """
    logger.info(
        "--maximum-gap-width=%s --snapping-distance=%s --debug=%s",
        maximum_gap_width,
        snapping_distance,
        debug,
    )
    try:
        _topo_clean(
            input_file,
            Path(output_file) if output_file is not None else None,
            Path(issues_file) if issues_file is not None else None,
            maximum_gap_width=maximum_gap_width,
            snapping_distance=snapping_distance,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
        )
    except (FileExistsError, ValueError, RuntimeError) as e:
        raise click.ClickException(str(e)) from e


@cli.command()
@click.argument("old_file", envvar="OLD_FILE")
@click.argument("new_file", envvar="NEW_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--overlay-file",
    envvar="OVERLAY_FILE",
    default=None,
    help='Spatial overlay layer path. Defaults to OUTPUT_FILE with an "_overlay" '
    "suffix.",
)
@click.option(
    "--tau-match",
    envvar="TAU_MATCH",
    type=float,
    default=TAU_MATCH_DEFAULT,
    show_default=True,
    help="Minimum overlap coverage for two units to be spatially linked.",
)
@click.option(
    "--tau-same",
    envvar="TAU_SAME",
    type=float,
    default=TAU_SAME_DEFAULT,
    show_default=True,
    help="Minimum IoU for a 1:1 linked pair to be unchanged/renamed rather than "
    "modified.",
)
@click.option(
    "--link-by-code",
    envvar="LINK_BY_CODE",
    is_flag=True,
    help="Also link units sharing a unique code value across versions.",
)
@click.option(
    "--link-by-name",
    envvar="LINK_BY_NAME",
    is_flag=True,
    help="Also link units sharing a unique name value across versions.",
)
@click.option(
    "--link-mode",
    envvar="LINK_MODE",
    type=click.Choice(["either", "both"]),
    default="either",
    show_default=True,
    help="How code/name identity matches combine (only matters if both flags are set).",
)
@click.option(
    "--code-column-a",
    envvar="CODE_COLUMN_A",
    default=None,
    help="Old-side code column; auto-detected if omitted.",
)
@click.option(
    "--code-column-b",
    envvar="CODE_COLUMN_B",
    default=None,
    help="New-side code column; auto-detected if omitted.",
)
@click.option(
    "--name-column-a",
    envvar="NAME_COLUMN_A",
    default=None,
    help="Old-side name column; auto-detected if omitted.",
)
@click.option(
    "--name-column-b",
    envvar="NAME_COLUMN_B",
    default=None,
    help="New-side name column; auto-detected if omitted.",
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "overlap", "classify", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
def change(  # noqa: PLR0913, PLR0917
    old_file: str,
    new_file: str,
    output_file: str | None,
    overlay_file: str | None,
    tau_match: float,
    tau_same: float,
    link_by_code: bool,  # noqa: FBT001
    link_by_name: bool,  # noqa: FBT001
    link_mode: str,
    code_column_a: str | None,
    code_column_b: str | None,
    name_column_a: str | None,
    name_column_b: str | None,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
) -> None:
    """Compare two polygon layer versions and classify what changed.

    OLD_FILE is the previous version, NEW_FILE is the new version. OUTPUT_FILE
    (the tabular changelog, CSV or Parquet) defaults to a name combining both
    stems with a "_changelog" suffix if omitted. A spatial overlay layer
    colored by relationship_class is always written alongside it.

    \b
    Examples:
      # Basic run, pure spatial matching
      topo-tools change admin2_2020.geojson admin2_2024.geojson

    \b
      # Also link units sharing a unique pcode across versions
      topo-tools change old.gpkg new.gpkg --link-by-code

    \b
      # Loosen the "related" threshold for heavily redrawn boundaries
      topo-tools change old.parquet new.parquet --tau-match 0.6
    """
    logger.info("--tau-match=%s --tau-same=%s --debug=%s", tau_match, tau_same, debug)
    try:
        _change(
            old_file,
            new_file,
            Path(output_file) if output_file is not None else None,
            Path(overlay_file) if overlay_file is not None else None,
            tau_match=tau_match,
            tau_same=tau_same,
            link_by_code=link_by_code,
            link_by_name=link_by_name,
            link_mode=link_mode,
            code_column_a=code_column_a,
            code_column_b=code_column_b,
            name_column_a=name_column_a,
            name_column_b=name_column_b,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
        )
    except (FileExistsError, ValueError, RuntimeError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="code-create")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.argument("issues_file", envvar="ISSUES_FILE", required=False, default=None)
@click.option("--root-code", envvar="ROOT_CODE", required=True, help="Root code value.")
@click.option(
    "--delimiter",
    envvar="DELIMITER",
    required=True,
    help="Single-character delimiter, or empty ('') for none.",
)
@click.option(
    "--min-width",
    envvar="MIN_WIDTH",
    required=True,
    help="Zero-pad floor per level: one width (3), one per level, coarsest "
    "first (2,2,4), or auto (the digits each level needs).",
)
@click.option(
    "--source-codes",
    envvar="SOURCE_CODES",
    type=click.Choice(["replace", "embed", "copy"]),
    default="replace",
    show_default=True,
    help="Each level's existing code: replace it, embed it as the level's own "
    "component, or copy it to a numbered sibling column before replacing it.",
)
@click.option(
    "--name-field",
    envvar="NAME_FIELD",
    default=None,
    help="Name-field template, e.g. 'adm{n}_name' (requires --code-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--code-field",
    envvar="CODE_FIELD",
    default=None,
    help="Code-field template, e.g. 'adm{n}_code' (requires --name-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "levels", "assign", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
def code_create(  # noqa: PLR0913, PLR0917
    input_file: str,
    output_file: str | None,
    issues_file: str | None,
    root_code: str,
    delimiter: str,
    min_width: str,
    source_codes: str,
    name_field: str | None,
    code_field: str | None,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
) -> None:
    """Cold-start a hierarchical code on one input file, ranked per parent.

    Each level's own code column is written into in place, no separate
    output-naming flag; OUTPUT_FILE defaults to INPUT_FILE with a "_coded"
    suffix. ISSUES_FILE (tabular, overflow rows only) defaults to
    OUTPUT_FILE with an "_issues" suffix, written only when non-empty.

    \b
    Examples:
      # Default naming, levels auto-detected structurally
      topo-tools code-create admin2.geojson --root-code AFG --delimiter . \\
        --min-width 3

    \b
      # Explicit code/name columns, when auto-detection is ambiguous
      topo-tools code-create admin2.geojson --root-code AFG --delimiter . \\
        --min-width 3 --code-field adm{n}_code --name-field adm{n}_name

    \b
      # Source codes kept inside the code, no delimiter (AF01, AF0101, ...)
      topo-tools code-create admin2.geojson --root-code AF --delimiter '' \\
        --min-width 2 --source-codes embed --code-field adm{n}_code \\
        --name-field adm{n}_name
    """
    logger.info("--debug=%s", debug)
    try:
        _code_create(
            input_file,
            Path(output_file) if output_file is not None else None,
            Path(issues_file) if issues_file is not None else None,
            root_code=root_code,
            delimiter=delimiter,
            min_width=min_width,
            source_codes=source_codes,
            name_field=name_field,
            code_field=code_field,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
        )
    except (FileExistsError, ValueError, RuntimeError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="code-update")
@click.argument("old_file", envvar="OLD_FILE")
@click.argument("new_file", envvar="NEW_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.argument("changelog_file", envvar="CHANGELOG_FILE", required=False, default=None)
@click.option(
    "--root-code",
    envvar="ROOT_CODE",
    default=None,
    help="Root code value; auto-detected off OLD's own codes if omitted.",
)
@click.option(
    "--delimiter",
    envvar="DELIMITER",
    default=None,
    help="Single-character delimiter; auto-detected off OLD's own codes if omitted.",
)
@click.option(
    "--min-width",
    envvar="MIN_WIDTH",
    default=None,
    help="Zero-pad floor per level: 3, 2,2,4 or auto; detected off OLD's own "
    "codes if omitted.",
)
@click.option(
    "--name-field-a",
    envvar="NAME_FIELD_A",
    default=None,
    help="OLD name-field template, e.g. 'adm{n}_name' (requires --code-field-a; "
    "default: structural auto-detection).",
)
@click.option(
    "--code-field-a",
    envvar="CODE_FIELD_A",
    default=None,
    help="OLD code-field template, e.g. 'adm{n}_pcode' (requires --name-field-a; "
    "default: structural auto-detection).",
)
@click.option(
    "--name-field-b",
    envvar="NAME_FIELD_B",
    default=None,
    help="NEW name-field template (requires --code-field-b; "
    "default: structural auto-detection).",
)
@click.option(
    "--code-field-b",
    envvar="CODE_FIELD_B",
    default=None,
    help="NEW code-field template (requires --name-field-b; "
    "default: structural auto-detection).",
)
@click.option(
    "--code-column-a",
    envvar="CODE_COLUMN_A",
    default=None,
    help="Old-side identity-link code column; defaults to the resolved per-level "
    "code column.",
)
@click.option(
    "--code-column-b",
    envvar="CODE_COLUMN_B",
    default=None,
    help="New-side identity-link code column; defaults to the resolved per-level "
    "code column.",
)
@click.option(
    "--name-column-a",
    envvar="NAME_COLUMN_A",
    default=None,
    help="Old-side identity-link name column; defaults to the resolved per-level "
    "name column.",
)
@click.option(
    "--name-column-b",
    envvar="NAME_COLUMN_B",
    default=None,
    help="New-side identity-link name column; defaults to the resolved per-level "
    "name column.",
)
@click.option(
    "--tau-match",
    envvar="TAU_MATCH",
    type=float,
    default=TAU_MATCH_DEFAULT,
    show_default=True,
    help="Minimum overlap coverage for two units to be spatially linked.",
)
@click.option(
    "--tau-same",
    envvar="TAU_SAME",
    type=float,
    default=TAU_SAME_DEFAULT,
    show_default=True,
    help="Minimum IoU for a 1:1 linked pair to be unchanged/renamed rather than "
    "modified.",
)
@click.option(
    "--link-by-code",
    envvar="LINK_BY_CODE",
    is_flag=True,
    help="Also link units sharing a unique code value across versions.",
)
@click.option(
    "--link-by-name",
    envvar="LINK_BY_NAME",
    is_flag=True,
    help="Also link units sharing a unique name value across versions.",
)
@click.option(
    "--link-mode",
    envvar="LINK_MODE",
    type=click.Choice(["either", "both"]),
    default="either",
    show_default=True,
    help="How code/name identity matches combine (only matters if both flags are set).",
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "levels", "process", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
def code_update(  # noqa: PLR0913, PLR0917
    old_file: str,
    new_file: str,
    output_file: str | None,
    changelog_file: str | None,
    root_code: str | None,
    delimiter: str | None,
    min_width: str | None,
    name_field_a: str | None,
    code_field_a: str | None,
    name_field_b: str | None,
    code_field_b: str | None,
    code_column_a: str | None,
    code_column_b: str | None,
    name_column_a: str | None,
    name_column_b: str | None,
    tau_match: float,
    tau_same: float,
    link_by_code: bool,  # noqa: FBT001
    link_by_name: bool,  # noqa: FBT001
    link_mode: str,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
) -> None:
    """Reconcile an already-coded OLD layer against an uncoded NEW candidate.

    OLD_FILE is the previous already-coded version, NEW_FILE is the uncoded
    candidate version. OUTPUT_FILE (NEW's geometry, coded) defaults to
    NEW_FILE with a "_coded" suffix. CHANGELOG_FILE (tabular, always written)
    defaults to OUTPUT_FILE with a "_changelog" suffix.

    \b
    Examples:
      # Basic run, format and levels auto-detected off OLD's own codes
      topo-tools code-update admin1_old.geojson admin1_new.geojson

    \b
      # Identity-link on a shared source code, for relocated units
      topo-tools code-update old.gpkg new.gpkg --link-by-code \\
        --code-column-a srcid --code-column-b srcid
    """
    logger.info("--debug=%s", debug)
    try:
        _code_update(
            old_file,
            new_file,
            Path(output_file) if output_file is not None else None,
            Path(changelog_file) if changelog_file is not None else None,
            root_code=root_code,
            delimiter=delimiter,
            min_width=min_width,
            name_field_a=name_field_a,
            code_field_a=code_field_a,
            name_field_b=name_field_b,
            code_field_b=code_field_b,
            code_column_a=code_column_a,
            code_column_b=code_column_b,
            name_column_a=name_column_a,
            name_column_b=name_column_b,
            tau_match=tau_match,
            tau_same=tau_same,
            link_by_code=link_by_code,
            link_by_name=link_by_name,
            link_mode=link_mode,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
        )
    except (FileExistsError, ValueError, RuntimeError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="edge-match")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("overlay_file", envvar="OVERLAY_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--input",
    "extra_inputs",
    envvar="EXTRA_INPUTS",
    multiple=True,
    help=(
        "Additional input file beyond INPUT_FILE, combined with it "
        "[may be repeated, and each value MAY be comma-separated]."
    ),
)
@click.option(
    "--issues-file",
    envvar="ISSUES_FILE",
    default=None,
    help='Issues report path. Defaults to OUTPUT_FILE with an "_issues" suffix.',
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "assign", "groups", "clip", "stitch", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
@click.option(
    "--match-column",
    envvar="MATCH_COLUMN",
    default=None,
    help=(
        "Column name shared by both layers, used as an exact code join "
        "(e.g. a pcode) that wins over spatial overlap on disagreement. "
        "Mutually exclusive with --overlay-match-column/--input-match-column."
    ),
)
@click.option(
    "--overlay-match-column",
    envvar="OVERLAY_MATCH_COLUMN",
    default=None,
    help="Overlay-side code column, when it's named differently than the input's.",
)
@click.option(
    "--input-match-column",
    envvar="INPUT_MATCH_COLUMN",
    default=None,
    help="Input-side code column, when it's named differently than the overlay's.",
)
@_add_merge_options
@click.option(
    "--per-feature",
    envvar="PER_FEATURE",
    is_flag=True,
    help=(
        "Assign each input feature independently to whichever overlay feature "
        "it overlaps most (assign-many), instead of forcing the whole input "
        "file onto one majority-vote overlay feature (assign-one, the default). "
        "Use this when input features genuinely belong to different overlay "
        "features, e.g. a "
        "poorly-digitized admin4 layer fitting into many admin3 units. "
        "Rejected when more than one input file resolves."
    ),
)
@_add_fill_options
def edge_match(  # noqa: PLR0913, PLR0917
    input_file: str,
    overlay_file: str,
    output_file: str | None,
    extra_inputs: tuple[str, ...],
    issues_file: str | None,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
    match_column: str | None,
    overlay_match_column: str | None,
    input_match_column: str | None,
    merge: bool,  # noqa: FBT001
    overlay_include: str | None,
    overlay_exclude: str | None,
    input_include: str | None,
    input_exclude: str | None,
    prefer: str | None,
    per_feature: bool,  # noqa: FBT001
    fill_schema: bool,  # noqa: FBT001
    name_field: str | None,
    code_field: str | None,
    depth_column: str,
) -> None:
    """Match one or more input layers to an overlay layer by largest overlap.

    OUTPUT_FILE defaults to INPUT_FILE with a "_matched" suffix if omitted;
    it is required when INPUT_FILE is a glob matching more than one file, or
    when --input is given.

    \b
    Examples:
      # Fit an admin4 layer into a single country boundary
      topo-tools edge-match adm4.geojson adm0.geojson

    \b
      # Fit admin3 into admin2 groups, each cleaned against its own overlay feature
      topo-tools edge-match adm3.gpkg adm2.gpkg adm3_matched.gpkg

    \b
      # Combine several raw countries' admin1 layers, matched and extended
      # together against one shared overlay
      topo-tools edge-match sen_adm1.parquet world_adm0.geojson out.parquet \\
        --input gmb_adm1.parquet,gnb_adm1.parquet

    \b
      # Prefer an existing pcode join over spatial overlap where they disagree
      topo-tools edge-match adm3.gpkg adm2.gpkg --match-column pcode

    \b
      # Copy just iso_3/adm0_name onto every matched input feature
      topo-tools edge-match adm3.gpkg adm2.gpkg \\
        --merge --overlay-include iso_3,adm0_name

    \b
      # Keep the overlay's version automatically on a name collision
      topo-tools edge-match adm3.gpkg adm2.gpkg --merge --prefer overlay

    \b
      # A poorly-digitized admin4 layer whose features legitimately
      # scatter across many different admin3 units
      topo-tools edge-match adm4.gpkg adm3.gpkg --per-feature
    """
    logger.info("--debug=%s", debug)
    if any(ch in input_file for ch in "*?["):
        matches = sorted(glob.glob(input_file, recursive=True))  # noqa: PTH207 (arbitrary pattern, not anchored to one Path)
        if not matches:
            msg = f"no files matched: {input_file}"
            raise click.ClickException(msg)
        base_inputs = [Path(p) for p in matches]
    else:
        base_inputs = [input_file]
    all_inputs = base_inputs + list(_split_commas(extra_inputs))
    resolved_input: str | Path | list[str | Path] = (
        all_inputs[0] if len(all_inputs) == 1 else all_inputs
    )
    try:
        _edge_match(
            resolved_input,
            overlay_file,
            Path(output_file) if output_file is not None else None,
            Path(issues_file) if issues_file is not None else None,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
            match_column=match_column,
            overlay_match_column=overlay_match_column,
            input_match_column=input_match_column,
            merge=merge,
            overlay_include=_split_columns(overlay_include),
            overlay_exclude=_split_columns(overlay_exclude),
            input_include=_split_columns(input_include),
            input_exclude=_split_columns(input_exclude),
            prefer=prefer,
            per_feature=per_feature,
            fill_schema=fill_schema,
            name_field=name_field,
            code_field=code_field,
            depth_column=depth_column,
        )
    except (FileExistsError, RuntimeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="edge-mosaic")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("overlay_file", envvar="OVERLAY_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--input",
    "extra_inputs",
    envvar="EXTRA_INPUTS",
    multiple=True,
    help=(
        "Additional input file beyond INPUT_FILE, combined with it "
        "[may be repeated, and each value MAY be comma-separated]."
    ),
)
@click.option(
    "--original",
    "original_files",
    envvar="ORIGINAL_FILES",
    multiple=True,
    help=(
        "Pre-extension original layer, used to decide whether a clip-detached "
        "piece merges; without it every such piece is only reported [may be "
        "repeated, and each value MAY be comma-separated]."
    ),
)
@click.option(
    "--issues-file",
    envvar="ISSUES_FILE",
    default=None,
    help='Issues report path. Defaults to OUTPUT_FILE with an "_issues" suffix.',
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "assign", "clip", "stitch", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
@click.option(
    "--match-column",
    envvar="MATCH_COLUMN",
    default=None,
    help=(
        "Column name shared by both layers, used as an exact code join "
        "(e.g. a pcode) that wins over spatial overlap on disagreement. "
        "Mutually exclusive with --overlay-match-column/--input-match-column."
    ),
)
@click.option(
    "--overlay-match-column",
    envvar="OVERLAY_MATCH_COLUMN",
    default=None,
    help="Overlay-side code column, when it's named differently than the input's.",
)
@click.option(
    "--input-match-column",
    envvar="INPUT_MATCH_COLUMN",
    default=None,
    help="Input-side code column, when it's named differently than the overlay's.",
)
@_add_merge_options
@_add_fill_options
def edge_mosaic(  # noqa: PLR0913, PLR0917
    input_file: str,
    overlay_file: str,
    output_file: str | None,
    extra_inputs: tuple[str, ...],
    original_files: tuple[str, ...],
    issues_file: str | None,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
    match_column: str | None,
    overlay_match_column: str | None,
    input_match_column: str | None,
    merge: bool,  # noqa: FBT001
    overlay_include: str | None,
    overlay_exclude: str | None,
    input_include: str | None,
    input_exclude: str | None,
    prefer: str | None,
    fill_schema: bool,  # noqa: FBT001
    name_field: str | None,
    code_field: str | None,
    depth_column: str,
) -> None:
    """Fit an already-extended input layer into a new overlay layer.

    OUTPUT_FILE defaults to INPUT_FILE with a "_mosaicked" suffix if omitted;
    it is required when INPUT_FILE is a glob matching more than one file, or
    when --input is given.

    \b
    Examples:
      # Re-clip a pre-extended admin3 layer against a new admin0 boundary
      topo-tools edge-mosaic adm3_extended.parquet adm0_new.geojson

    \b
      # Combine every country's pre-extended layer, re-clip against a world admin0
      topo-tools edge-mosaic "*/latest/adm2/extended.parquet" world_adm0.geojson \\
        out.parquet

    \b
      # Combine explicit files instead of a glob (--input MAY be repeated
      # and/or comma-separated)
      topo-tools edge-mosaic afg.parquet world_adm0.geojson out.parquet \\
        --input ago.parquet,are.parquet

    \b
      # Prefer an existing pcode join over spatial overlap where they disagree
      topo-tools edge-mosaic adm3_extended.parquet adm0_new.geojson --match-column pcode

    \b
      # Keep an overlay feature's own boundary when no input file covers it
      topo-tools edge-mosaic "*/latest/adm4/extended.parquet" world_adm0.geojson \\
        out.parquet --merge

    \b
      # Keep the overlay's version automatically on a name collision
      topo-tools edge-mosaic adm3_extended.parquet adm0_new.geojson \\
        --merge --prefer overlay
    """
    logger.info("--debug=%s", debug)
    if any(ch in input_file for ch in "*?["):
        matches = sorted(glob.glob(input_file, recursive=True))  # noqa: PTH207 (arbitrary pattern, not anchored to one Path)
        if not matches:
            msg = f"no files matched: {input_file}"
            raise click.ClickException(msg)
        base_inputs = [Path(p) for p in matches]
    else:
        base_inputs = [input_file]
    all_inputs = base_inputs + list(_split_commas(extra_inputs))
    resolved_input: str | Path | list[str | Path] = (
        all_inputs[0] if len(all_inputs) == 1 else all_inputs
    )
    try:
        _edge_mosaic(
            resolved_input,
            overlay_file,
            Path(output_file) if output_file is not None else None,
            Path(issues_file) if issues_file is not None else None,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
            match_column=match_column,
            overlay_match_column=overlay_match_column,
            input_match_column=input_match_column,
            merge=merge,
            overlay_include=_split_columns(overlay_include),
            overlay_exclude=_split_columns(overlay_exclude),
            input_include=_split_columns(input_include),
            input_exclude=_split_columns(input_exclude),
            prefer=prefer,
            fill_schema=fill_schema,
            name_field=name_field,
            code_field=code_field,
            depth_column=depth_column,
            original_paths=_split_commas(original_files) or None,
        )
    except (FileExistsError, RuntimeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="edge-stitch")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--input",
    "extra_inputs",
    envvar="EXTRA_INPUTS",
    multiple=True,
    help=(
        "Additional already-tiled file beyond INPUT_FILE, combined with it "
        "[may be repeated, and each value MAY be comma-separated]."
    ),
)
@click.option(
    "--issues-file",
    envvar="ISSUES_FILE",
    default=None,
    help='Issues report path. Defaults to OUTPUT_FILE with an "_issues" suffix.',
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "clean", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
@_add_fill_options
def edge_stitch(  # noqa: PLR0913, PLR0917
    input_file: str,
    output_file: str | None,
    extra_inputs: tuple[str, ...],
    issues_file: str | None,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
    fill_schema: bool,  # noqa: FBT001
    name_field: str | None,
    code_field: str | None,
    depth_column: str,
) -> None:
    """Close seams in an already-tiled polygon layer via coverage-clean.

    OUTPUT_FILE defaults to INPUT_FILE with a "_stitched" suffix if omitted;
    it is required when INPUT_FILE is a glob matching more than one file, or
    when --input is given.

    \b
    Examples:
      # Basic run, output name chosen automatically
      topo-tools edge-stitch tiled.geojson

    \b
      # Explicit output
      topo-tools edge-stitch tiled.gpkg stitched.gpkg

    \b
      # Combine every already-clipped file into one global stitched output
      topo-tools edge-stitch "tmp/clipped/*.parquet" stitched.parquet

    \b
      # Combine explicit files instead of a glob (--input MAY be repeated
      # and/or comma-separated)
      topo-tools edge-stitch afg.parquet stitched.parquet \\
        --input ago.parquet,are.parquet

    \b
      # Error instead of silently overwriting an existing output
      topo-tools edge-stitch tiled.parquet stitched.parquet --overwrite=false
    """
    logger.info("--debug=%s", debug)
    if any(ch in input_file for ch in "*?["):
        matches = sorted(glob.glob(input_file, recursive=True))  # noqa: PTH207 (arbitrary pattern, not anchored to one Path)
        if not matches:
            msg = f"no files matched: {input_file}"
            raise click.ClickException(msg)
        base_inputs = [Path(p) for p in matches]
    else:
        base_inputs = [input_file]
    all_inputs = base_inputs + list(_split_commas(extra_inputs))
    resolved_input: str | Path | list[str | Path] = (
        all_inputs[0] if len(all_inputs) == 1 else all_inputs
    )
    try:
        _edge_stitch(
            resolved_input,
            Path(output_file) if output_file is not None else None,
            Path(issues_file) if issues_file is not None else None,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
            fill_schema=fill_schema,
            name_field=name_field,
            code_field=code_field,
            depth_column=depth_column,
        )
    except (FileExistsError, RuntimeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="schema-fill")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--name-field",
    envvar="NAME_FIELD",
    default=None,
    help="Name-field template, e.g. 'adm{n}_name' (requires --code-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--code-field",
    envvar="CODE_FIELD",
    default=None,
    help="Code-field template, e.g. 'adm{n}_code' (requires --name-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "fill", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
@click.option(
    "--depth-column",
    envvar="DEPTH_COLUMN",
    default="adm_lvl",
    show_default=True,
    help="Name of the new column stamping each row's real, pre-fill depth.",
)
def schema_fill(  # noqa: PLR0913, PLR0917
    input_file: str,
    output_file: str | None,
    name_field: str | None,
    code_field: str | None,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
    depth_column: str,
) -> None:
    """Cascade each admin-hierarchy column down from its nearest shallower level.

    Pinned to each row's own real depth; stamps a new depth column ("adm_lvl").
    """
    logger.info("--debug=%s", debug)
    try:
        _schema_fill(
            input_file,
            Path(output_file) if output_file is not None else None,
            name_field=name_field,
            code_field=code_field,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
            depth_column=depth_column,
        )
    except (FileExistsError, RuntimeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="schema-join")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("join_file", envvar="JOIN_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--issues-output",
    envvar="ISSUES_OUTPUT",
    default=None,
    help="Issues report path (default: OUTPUT_FILE with an '_issues' suffix).",
)
@click.option(
    "--name-field",
    envvar="NAME_FIELD",
    default=None,
    help="Name-field template, e.g. 'adm{n}_name' (requires --code-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--code-field",
    envvar="CODE_FIELD",
    default=None,
    help="Code-field template, e.g. 'adm{n}_code' (requires --name-field; "
    "default: structural auto-detection).",
)
@click.option(
    "--min-overlap",
    envvar="MIN_OVERLAP",
    type=float,
    default=MIN_OVERLAP_DEFAULT,
    show_default=True,
    help=(
        "Flag an input feature whose best join feature covers less than "
        "this share of its area."
    ),
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "assign", "join", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
def schema_join(  # noqa: PLR0913, PLR0917
    input_file: str,
    join_file: str,
    output_file: str | None,
    issues_output: str | None,
    name_field: str | None,
    code_field: str | None,
    min_overlap: float,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
) -> None:
    """Copy each input feature's best-overlap join feature's hierarchy columns onto it.

    Geometry is never modified; conflicting values are kept side by side.
    """
    logger.info("--debug=%s", debug)
    try:
        _schema_join(
            input_file,
            join_file,
            Path(output_file) if output_file is not None else None,
            issues_path=Path(issues_output) if issues_output is not None else None,
            name_field=name_field,
            code_field=code_field,
            min_overlap=min_overlap,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
        )
    except (FileExistsError, RuntimeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="schema-map")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--csv",
    "csv_input",
    envvar="CSV",
    default=None,
    help="Apply this (edited) crosswalk CSV instead of mapping one; output "
    "columns follow its row order.",
)
@click.option(
    "--csv-output",
    envvar="CSV_OUTPUT",
    default=None,
    help="Where to write the mapped crosswalk CSV (default: INPUT_FILE with a "
    "'_crosswalk.csv' name).",
)
@click.option(
    "--map-only",
    envvar="MAP_ONLY",
    is_flag=True,
    help="Only write the crosswalk CSV, not the mapped layer.",
)
@click.option(
    "--name-field",
    envvar="NAME_FIELD",
    default=None,
    help="Name-field template, e.g. 'adm{n}_name' (requires --code-field; "
    "default: 'adm{n}_name').",
)
@click.option(
    "--code-field",
    envvar="CODE_FIELD",
    default=None,
    help="Code-field template, e.g. 'adm{n}_code' (requires --name-field; "
    "default: 'adm{n}_code').",
)
@click.option(
    "--level",
    envvar="LEVEL",
    type=click.IntRange(min=0),
    default=None,
    help="The file's own admin level, numbering its finest level (default: "
    "coarsest level numbered 1, a single-value country column 0).",
)
@click.option(
    "--layer",
    envvar="LAYER",
    default=None,
    help="Layer name, for a multi-layer source (e.g. FileGDB). Auto-detected "
    "when possible; required if auto-detection can't resolve it to exactly "
    "one geometry-bearing layer.",
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "map", "apply", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
def schema_map(  # noqa: PLR0913, PLR0917
    input_file: str,
    output_file: str | None,
    csv_input: str | None,
    csv_output: str | None,
    map_only: bool,  # noqa: FBT001
    name_field: str | None,
    code_field: str | None,
    level: int | None,
    layer: str | None,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
) -> None:
    """Map columns onto a target schema: rename/drop them via a crosswalk.

    By default, maps a crosswalk from the file's structure, writes it as CSV,
    and applies it. To iterate, edit the CSV (retarget, blank to drop, move
    rows to reorder) and re-run with --csv. --map-only writes the CSV
    alone. OUTPUT_FILE defaults to INPUT_FILE with a "_mapped" suffix.
    Target names default to "adm{n}_name"/"adm{n}_code"; override with
    --name-field/--code-field.

    \b
    Examples:
      # Map and apply, output names chosen automatically
      topo-tools schema-map example.geojson

    \b
      # Apply an edited crosswalk
      topo-tools schema-map example.geojson --csv example_crosswalk.csv

    \b
      # Only write the crosswalk, numbering levels from the file's own level
      topo-tools schema-map admin3.geojson --map-only --level 3

    \b
      # Custom target field naming
      topo-tools schema-map example.geojson --name-field adm{n}_name \\
        --code-field adm{n}_pcode
    """
    logger.info("--debug=%s", debug)
    try:
        _schema_map(
            input_file,
            Path(output_file) if output_file is not None else None,
            csv_input=csv_input,
            csv_output=csv_output,
            map_only=map_only,
            name_field=name_field,
            code_field=code_field,
            level=level,
            layer=layer,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
        )
    except (FileExistsError, RuntimeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="edge-clip")
@click.argument("input_file", envvar="INPUT_FILE")
@click.argument("overlay_file", envvar="OVERLAY_FILE")
@click.argument("output_file", envvar="OUTPUT_FILE", required=False, default=None)
@click.option(
    "--issues-file",
    envvar="ISSUES_FILE",
    default=None,
    help=(
        "Issues report path, only used with --match-column/--overlay-match-column. "
        'Defaults to OUTPUT_FILE with an "_issues" suffix.'
    ),
)
@click.option(
    "--name",
    envvar="NAME",
    default=None,
    help="Run name for internal tables/tmp files.",
)
@click.option(
    "--overwrite",
    envvar="OVERWRITE",
    type=bool,
    default=True,
    show_default=True,
    help="Overwrite an existing output; pass --overwrite=false to error instead.",
)
@click.option(
    "--threads", envvar="THREADS", type=int, default=None, help="DuckDB thread count."
)
@click.option(
    "--debug",
    envvar="DEBUG",
    is_flag=True,
    help="Keep intermediate tables, export to Parquet, log timing/memory per query.",
)
@click.option(
    "--tmp-dir",
    envvar="TMP_DIR",
    default=None,
    help="Intermediate DuckDB + Parquet location.",
)
@click.option(
    "--step",
    envvar="STEP",
    type=click.Choice(["inputs", "assign", "clip", "outputs"]),
    default=None,
    help="Run only one named stage.",
)
@click.option(
    "--match-column",
    envvar="MATCH_COLUMN",
    default=None,
    help=(
        "Column name shared by both layers, used as an exact code join "
        "(e.g. a pcode) that wins over spatial overlap on disagreement. "
        "Mutually exclusive with --overlay-match-column/--input-match-column."
    ),
)
@click.option(
    "--overlay-match-column",
    envvar="OVERLAY_MATCH_COLUMN",
    default=None,
    help="Overlay-side code column, when it's named differently than the input's.",
)
@click.option(
    "--input-match-column",
    envvar="INPUT_MATCH_COLUMN",
    default=None,
    help="Input-side code column, when it's named differently than the overlay's.",
)
@click.option(
    "--carry-column",
    "carry_columns",
    envvar="CARRY_COLUMNS",
    multiple=True,
    help=(
        "Overlay column to copy onto each matched input feature [may be repeated, "
        "and each value MAY be comma-separated]."
    ),
)
@click.option(
    "--original",
    "original_file",
    envvar="ORIGINAL_FILE",
    default=None,
    help=(
        "Pre-extension original layer, used to decide whether a clip-detached "
        "piece merges; without it every such piece is only reported."
    ),
)
def edge_clip(  # noqa: PLR0913, PLR0917
    input_file: str,
    overlay_file: str,
    output_file: str | None,
    issues_file: str | None,
    name: str | None,
    overwrite: bool,  # noqa: FBT001
    threads: int | None,
    debug: bool,  # noqa: FBT001
    tmp_dir: str | None,
    step: str | None,
    match_column: str | None,
    overlay_match_column: str | None,
    input_match_column: str | None,
    carry_columns: tuple[str, ...],
    original_file: str | None,
) -> None:
    """Assign each input feature to an overlay feature, then clip it to that geometry.

    INPUT_FILE and OVERLAY_FILE are both raw polygon layers; INPUT_FILE's
    features are assigned to OVERLAY_FILE's features internally (assign-one)
    before clipping. OUTPUT_FILE defaults to INPUT_FILE with a "_clipped"
    suffix if omitted.

    \b
    Examples:
      # Clip an input layer against an overlay layer
      topo-tools edge-clip input.parquet adm1.geojson

    \b
      # Explicit output
      topo-tools edge-clip input.parquet adm1.geojson clipped.parquet

    \b
      # Prefer an existing pcode join over spatial overlap where they disagree
      topo-tools edge-clip input.parquet adm1.geojson --match-column pcode

    \b
      # Copy overlay columns onto every matched input feature
      topo-tools edge-clip input.parquet adm1.geojson --carry-column iso_3,adm0_name
    """
    logger.info("--debug=%s", debug)

    try:
        _edge_clip(
            input_file,
            overlay_file,
            Path(output_file) if output_file is not None else None,
            Path(issues_file) if issues_file is not None else None,
            name=name,
            threads=threads,
            tmp_dir=tmp_dir,
            overwrite=overwrite,
            debug=debug,
            step=step,
            match_column=match_column,
            overlay_match_column=overlay_match_column,
            input_match_column=input_match_column,
            carry_columns=_split_commas(carry_columns) or None,
            original_path=original_file,
        )
    except (FileExistsError, RuntimeError, ValueError) as e:
        raise click.ClickException(str(e)) from e
