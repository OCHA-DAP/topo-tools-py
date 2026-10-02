"""Counts each issues report by kind and severity, and writes the summary."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from topo_tools.core.code import TABLE_COPY_OPTS
from topo_tools.core.io import add_csv_bom
from topo_tools.core.validate._constants import STAGES, TOPO_SEVERITY

COLUMNS = (
    "stage VARCHAR, kind VARCHAR, severity VARCHAR, count INTEGER, "
    "report VARCHAR, reason VARCHAR"
)


def _literal(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def create(conn: DuckDBPyConnection) -> None:
    """Create the empty `summary` table."""
    conn.execute(f"CREATE OR REPLACE TABLE summary ({COLUMNS})")


def add_report(conn: DuckDBPyConnection, stage: str, report: Path) -> None:
    """Add one row per kind and severity in report, or one zero row if empty."""
    path = _literal(str(report))
    if report.suffix == ".csv":
        source = f"read_csv({path}, all_varchar = true)"
        severity = "severity"
    else:
        source = f"read_parquet({path})"
        cases = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in TOPO_SEVERITY.items())
        severity = f"CASE kind {cases} ELSE 'error' END"
    rows = (
        f"SELECT {_literal(stage)}, kind, {severity}, count(*), {path}, NULL "
        f"FROM {source} GROUP BY ALL"
        if report.exists()
        else "SELECT NULL, NULL, NULL, NULL, NULL, NULL WHERE false"
    )
    conn.execute(f"INSERT INTO summary {rows}")
    conn.execute(f"""--sql
        INSERT INTO summary
        SELECT {_literal(stage)}, NULL, NULL, 0, {path}, 'no issues'
        WHERE NOT EXISTS (SELECT 1 FROM summary WHERE stage = {_literal(stage)})
    """)


def add_outcome(
    conn: DuckDBPyConnection, stage: str, kind: str, severity: str, reason: str
) -> None:
    """Add a stage that didn't produce a report: failed or skipped."""
    conn.execute(
        "INSERT INTO summary VALUES (?, ?, ?, NULL, NULL, ?)",
        [stage, kind, severity, reason],
    )


def has_kind(conn: DuckDBPyConnection, stage: str, kinds: tuple[str, ...]) -> bool:
    """Check whether stage's rows include any of kinds."""
    return conn.execute(
        "SELECT count(*) > 0 FROM summary WHERE stage = ? AND list_contains(?, kind)",
        [stage, list(kinds)],
    ).fetchone()[0]


def write(conn: DuckDBPyConnection, dest: Path) -> list[tuple]:
    """Write the summary to dest and return its rows, errors first."""
    stages = ", ".join(f"'{s}'" for s in STAGES)
    order = f"ORDER BY list_position([{stages}], stage), severity, kind"
    dest.parent.mkdir(exist_ok=True, parents=True)
    conn.execute(
        f"COPY (SELECT * FROM summary {order}) TO {_literal(str(dest))} "
        f"{TABLE_COPY_OPTS[dest.suffix]}"
    )
    add_csv_bom(dest)
    return conn.execute(f"SELECT * FROM summary {order}").fetchall()
