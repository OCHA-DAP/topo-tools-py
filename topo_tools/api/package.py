"""Public API: run package-polygons, package-points, and package-lines in one call."""

from pathlib import Path

from topo_tools.api.package_lines import package_lines
from topo_tools.api.package_points import package_points
from topo_tools.api.package_polygons import package_polygons


def _substitute(output_path: str | Path | None, word: str) -> str | Path | None:
    if output_path is None:
        return None
    text = str(output_path)
    if "{x}" not in text:
        msg = f"output_path given without a literal '{{x}}' placeholder: {output_path}"
        raise ValueError(msg)
    return text.replace("{x}", word)


def package(  # noqa: PLR0913
    input_path: str | Path,
    output_path: str | Path | None = None,
    target_schema_path: str | Path | None = None,
    *,
    threads: int | None = None,
    tmp_dir: str | Path | None = None,
    overwrite: bool = True,
    debug: bool = False,
) -> None:
    """Run package-polygons, package-points, and package-lines against one input."""
    package_polygons(
        input_path,
        _substitute(output_path, "admin{n}"),
        target_schema_path=target_schema_path,
        threads=threads,
        tmp_dir=tmp_dir,
        overwrite=overwrite,
        debug=debug,
    )
    package_points(
        input_path,
        _substitute(output_path, "points"),
        target_schema_path,
        threads=threads,
        tmp_dir=tmp_dir,
        overwrite=overwrite,
        debug=debug,
    )
    package_lines(
        input_path,
        _substitute(output_path, "lines"),
        target_schema_path,
        threads=threads,
        tmp_dir=tmp_dir,
        overwrite=overwrite,
        debug=debug,
    )
