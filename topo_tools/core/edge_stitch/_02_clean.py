"""Whole-table ST_CoverageClean pass, closing seams between independent tiles."""

from duckdb import DuckDBPyConnection

from topo_tools.core.coverage import coverage_clean_escalating


def main(conn: DuckDBPyConnection, table_in: str, table_out: str) -> None:
    """Coverage-clean table_in into table_out, micro rows in `{table_out}_micro`."""
    coverage_clean_escalating(
        conn, table_in, table_out, fids=None, micro_issues_table=f"{table_out}_micro"
    )
