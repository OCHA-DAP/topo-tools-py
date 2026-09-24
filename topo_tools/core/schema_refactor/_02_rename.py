"""Renames/drops columns per the validated crosswalk."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from topo_tools.core.admin_columns import canonical_order
from topo_tools.core.duckdb_utils import quote_identifier

logger = getLogger(__name__)


def main(conn: DuckDBPyConnection, name: str, name_field: str, code_field: str) -> None:
    """Apply `{name}_crosswalk` to `{name}_01`, writing `{name}_02` in canonical order.

    A source column whose target_column is null/empty is dropped; every
    other source column is renamed to its target_column.
    """
    rows = conn.execute(
        f'SELECT source_column, target_column FROM "{name}_crosswalk"'
    ).fetchall()
    targets = {target: source for source, target in rows if target}
    columns, sort_column = canonical_order(list(targets), name_field, code_field)
    if sort_column is None:
        logger.warning(
            "schema-refactor: no %r target column; rows keep input order "
            "(pass --name-field/--code-field for another schema)",
            code_field,
        )
    select = "".join(
        f", {quote_identifier(targets[t])} AS {quote_identifier(t)}" for t in columns
    )
    # By position: a source column may share a name with a different target.
    order = f"{columns.index(sort_column) + 3} NULLS LAST, " if sort_column else ""
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02" AS
        SELECT fid, geom{select} FROM "{name}_01" ORDER BY {order}fid
    """)
