"""Exports the refactored output, plus an overflow issues report when non-empty."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from topo_tools.core.code import (
    TABLE_COPY_OPTS,
    CodeFormat,
    last_component,
    parent_prefix,
)
from topo_tools.core.io import export_geometry_table


def main(  # noqa: PLR0913
    conn: DuckDBPyConnection,
    table: str,
    dest: Path,
    *,
    levels: dict[int, str],
    fmt: CodeFormat,
    issues_dest: Path | None = None,
    debug: bool = False,
) -> None:
    """Export table to dest; write an overflow report to issues_dest if given."""
    export_geometry_table(conn, table, dest)

    if issues_dest is not None:
        _write_overflow_issues(conn, table, levels, fmt, issues_dest)

    if not debug:
        conn.execute(f'DROP TABLE IF EXISTS "{table}"')


def _write_overflow_issues(
    conn: DuckDBPyConnection,
    table: str,
    levels: dict[int, str],
    fmt: CodeFormat,
    issues_dest: Path,
) -> None:
    """Group each level's codes by parent, flag any group over min_width capacity."""
    capacity = 10**fmt.min_width - 1
    rows: list[tuple[str, int, str, str, int, int, str]] = []
    for level, code_column in levels.items():
        if level == 0:
            continue
        codes = [
            r[0]
            for r in conn.execute(
                f'SELECT DISTINCT "{code_column}" FROM "{table}"'
            ).fetchall()
        ]
        by_parent: dict[str, list[str]] = {}
        for code in codes:
            by_parent.setdefault(parent_prefix(code, fmt), []).append(code)
        for parent_code, children in by_parent.items():
            if len(children) <= capacity:
                continue
            assigned_code = max(children, key=lambda c: int(last_component(c, fmt)))
            reason = (
                f"{len(children)} children exceeds {capacity} "
                f"at min_width={fmt.min_width}"
            )
            rows.append(
                (
                    "digit-overflow",
                    level,
                    parent_code,
                    assigned_code,
                    len(children),
                    fmt.min_width,
                    reason,
                )
            )

    if not rows:
        issues_dest.unlink(missing_ok=True)
        return

    issues_table = f"{table}_issues"
    conn.execute(f"""--sql
        CREATE OR REPLACE TEMP TABLE "{issues_table}" (
            kind VARCHAR, level INTEGER, parent_code VARCHAR, assigned_code VARCHAR,
            child_count INTEGER, min_width INTEGER, reason VARCHAR
        )
    """)
    conn.executemany(f'INSERT INTO "{issues_table}" VALUES (?, ?, ?, ?, ?, ?, ?)', rows)
    conn.execute(
        f"COPY (SELECT * FROM \"{issues_table}\") TO '{issues_dest}' "
        f"{TABLE_COPY_OPTS[issues_dest.suffix]}"
    )
    conn.execute(f'DROP TABLE IF EXISTS "{issues_table}"')
