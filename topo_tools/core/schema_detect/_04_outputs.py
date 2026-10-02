"""Writes the schema issues report, even when empty."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from topo_tools.core.code import TABLE_COPY_OPTS
from topo_tools.core.io import add_csv_bom
from topo_tools.core.schema_detect._constants import SEVERITY

REPORT_SUFFIXES = (".csv", ".parquet")


def main(
    conn: DuckDBPyConnection, name: str, dest: Path, *, debug: bool = False
) -> None:
    """Write `{name}_04` to dest, one row per finding, keyed by kind."""
    severity = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in SEVERITY.items())
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_04" AS
        SELECT kind || '-' || row_number() OVER (
                   PARTITION BY kind ORDER BY level, column_name, code
               ) AS key,
               kind, CASE kind {severity} END AS severity, level,
               column_name AS "column", code, reason
        FROM "{name}_03"
        ORDER BY severity, level, kind, "column", code
    """)
    dest.parent.mkdir(exist_ok=True, parents=True)
    conn.execute(f"COPY \"{name}_04\" TO '{dest}' {TABLE_COPY_OPTS[dest.suffix]}")
    add_csv_bom(dest)
    if not debug:
        for suffix in ("01", "02", "03", "04"):
            conn.execute(f'DROP TABLE IF EXISTS "{name}_{suffix}"')
