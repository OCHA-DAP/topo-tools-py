"""Joins overlay_fid onto the combined input table, then clips per overlay fid."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from ._engine import main as clip_engine


def main(  # noqa: PLR0913
    conn: DuckDBPyConnection,
    name: str,
    tmp_dir: Path,
    *,
    threads: int | None = None,
    debug: bool = False,
    carry_columns: list[str] | None = None,
) -> None:
    """Clip each assigned input feature to its overlay, isolated per overlay fid."""
    carry_sql = "".join(f', a."{c}" AS "{c}"' for c in (carry_columns or []))
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02_clip_in" AS
        SELECT c.*, a.overlay_fid{carry_sql}
        FROM "{name}_input_01" c
        JOIN "{name}_02_assign" a ON a.input_fid = c.fid
    """)
    clip_engine(
        conn,
        f"{name}_02_clip_in",
        f'"{name}_overlay_01"',
        f"{name}_03",
        tmp_dir,
        threads=threads,
        debug=debug,
    )
    if not debug:
        conn.execute(f'DROP TABLE IF EXISTS "{name}_02_clip_in"')
