"""Renames/drops columns per the validated crosswalk."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from topo_tools.core.admin_columns import canonical_order, sibling_name
from topo_tools.core.duckdb_utils import quote_identifier

logger = getLogger(__name__)


def _misordered_siblings(columns: list[str]) -> list[str]:
    """Return each column whose numbered siblings aren't in numeric order after it."""
    position = {c: i for i, c in enumerate(columns)}
    misordered = []
    for base in columns:
        siblings = (sibling_name(base, k) for k in range(1, len(columns) + 1))
        family = [position[c] for c in [base, *siblings] if c in position]
        if family != sorted(family):
            misordered.append(base)
    return misordered


def main(
    conn: DuckDBPyConnection,
    name: str,
    name_field: str,
    code_field: str,
    *,
    row_order: bool = False,
) -> None:
    """Apply `{name}_crosswalk` to `{name}_01`, writing `{name}_02`.

    Columns follow the crosswalk's row order if row_order, else canonical order.
    """
    rows = conn.execute(f"""--sql
        SELECT source_column, target_column FROM "{name}_crosswalk"
        ORDER BY row_order
    """).fetchall()
    targets = {target: source for source, target in rows if target}
    columns, sort_column = canonical_order(list(targets), name_field, code_field)
    if row_order:
        columns = list(targets)
        if misordered := _misordered_siblings(columns):
            logger.warning(
                "schema-map: numbered siblings of %s are out of order in "
                "the crosswalk; output columns follow its row order",
                misordered,
            )
    if sort_column is None:
        logger.warning(
            "schema-map: no %r target column; rows keep input order "
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
