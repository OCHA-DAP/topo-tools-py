"""Classifies one level's OLD/NEW units via change's own overlap+classify stages."""

from duckdb import DuckDBPyConnection

from topo_tools.core.change import _02_overlap as overlap_stage
from topo_tools.core.change import _03_classify as classify_stage


def main(  # noqa: PLR0913
    conn: DuckDBPyConnection,
    name: str,
    n: int,
    *,
    tau_match: float,
    tau_same: float,
    link_by_code: bool,
    link_by_name: bool,
    link_mode: str,
    code_col_a: str | None,
    code_col_b: str | None,
    name_col_a: str | None,
    name_col_b: str | None,
) -> None:
    """Classify level n, writing `{name}_chg_{n}_03a`/`_03b`/`_03c`."""
    level_name = f"{name}_chg_{n}"
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{level_name}_a_01" AS
        SELECT * FROM "{name}_dsl_{n}_a"
    """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{level_name}_b_01" AS
        SELECT * FROM "{name}_dsl_{n}_b"
    """)
    overlap_stage.main(conn, level_name)
    classify_stage.main(
        conn,
        level_name,
        tau_match=tau_match,
        tau_same=tau_same,
        link_by_code=link_by_code,
        link_by_name=link_by_name,
        link_mode=link_mode,
        code_col_a=code_col_a,
        code_col_b=code_col_b,
        name_col_a=name_col_a,
        name_col_b=name_col_b,
    )
    conn.execute(f'DROP TABLE IF EXISTS "{level_name}_a_01"')
    conn.execute(f'DROP TABLE IF EXISTS "{level_name}_b_01"')
