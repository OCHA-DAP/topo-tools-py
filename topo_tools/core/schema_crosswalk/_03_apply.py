"""Applies a crosswalk to `{name}_01` via core.schema_refactor's rename stage."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from topo_tools.core.schema_map._target_schema import TargetSchema
from topo_tools.core.schema_refactor._01_inputs import (
    parse_crosswalk,
    validate_and_materialize_crosswalk,
)
from topo_tools.core.schema_refactor._02_rename import main as rename_main


def main(
    conn: DuckDBPyConnection,
    name: str,
    path: Path | str,
    schema: TargetSchema,
    csv_input: Path | None = None,
) -> None:
    """Rename/drop `{name}_01`'s columns, writing `{name}_apply_02`.

    Applies csv_input in row order if given, else `{name}_02` canonically.
    """
    apply_name = f"{name}_apply"
    conn.execute(f"""--sql
        CREATE OR REPLACE VIEW "{apply_name}_01" AS SELECT * FROM "{name}_01"
    """)

    if csv_input is None:
        rows = conn.execute(f"""--sql
            SELECT source_column, target_column FROM "{name}_02"
            WHERE source_column IS NOT NULL
        """).fetchall()
        crosswalk = [{"source_column": r[0], "target_column": r[1]} for r in rows]
    else:
        crosswalk = parse_crosswalk(csv_input)

    validate_and_materialize_crosswalk(
        conn, apply_name, f"{apply_name}_01", crosswalk, path
    )
    rename_main(
        conn,
        apply_name,
        schema.name_field,
        schema.code_field,
        row_order=csv_input is not None,
    )
    # Drop now, right after use: a later DROP TABLE IF EXISTS on this name
    # (core.refactor._03_outputs's own cleanup) errors on a view, not a table.
    conn.execute(f'DROP VIEW IF EXISTS "{apply_name}_01"')
