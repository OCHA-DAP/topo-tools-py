"""Infers a CodeFormat directly from a column's own already-assigned code values."""

from collections import Counter

from duckdb import DuckDBPyConnection

from topo_tools.core.code._code_format import CodeFormat, MinWidth

_SAMPLE_LIMIT = 10_000


def detect_code_format(
    conn: DuckDBPyConnection, table: str, code_column: str
) -> CodeFormat:
    """Infer delimiter/root_code/min_width from code_column's own existing values."""
    rows = conn.execute(f"""--sql
        SELECT DISTINCT "{code_column}" FROM "{table}"
        WHERE "{code_column}" IS NOT NULL
        LIMIT {_SAMPLE_LIMIT}
    """).fetchall()
    codes = [r[0] for r in rows]
    if not codes:
        msg = f"no non-null values in {code_column!r} to detect a code format from"
        raise ValueError(msg)

    delimiter = _detect_delimiter(codes, code_column)
    root_code = _detect_root(codes, delimiter, code_column)
    min_width = _detect_min_width(codes, delimiter, code_column)
    return CodeFormat(root_code=root_code, delimiter=delimiter, min_width=min_width)


def has_delimiter(conn: DuckDBPyConnection, table: str, code_column: str) -> bool:
    """Return whether any sampled code in code_column has a non-alphanumeric char."""
    return (
        conn.execute(f"""--sql
        SELECT bool_or(regexp_matches("{code_column}"::VARCHAR, '[^A-Za-z0-9]'))
        FROM (
            SELECT DISTINCT "{code_column}" FROM "{table}"
            WHERE "{code_column}" IS NOT NULL LIMIT {_SAMPLE_LIMIT}
        )
    """).fetchone()[0]
        is True
    )


def detect_undelimited_format(
    conn: DuckDBPyConnection, table: str, level_columns: dict[int, str]
) -> CodeFormat:
    """Infer root and per-level widths from one code column per level, no delimiter."""
    levels = sorted(level_columns)
    roots = {
        r[0]
        for r in conn.execute(f"""--sql
            SELECT DISTINCT regexp_extract("{level_columns[levels[0]]}"::VARCHAR,
                                           '^[^0-9]*')
            FROM "{table}" WHERE "{level_columns[levels[0]]}" IS NOT NULL
        """).fetchall()
    }
    if len(roots) != 1 or not next(iter(roots)):
        msg = (
            f"{level_columns[levels[0]]!r} does not share one non-numeric root "
            f"(found {sorted(roots)}); pass --root-code explicitly"
        )
        raise ValueError(msg)
    root_code = next(iter(roots))
    widths = []
    parent_sql = str(len(root_code))
    for n in levels:
        column = level_columns[n]
        found = [
            r[0]
            for r in conn.execute(f"""--sql
                SELECT DISTINCT length("{column}"::VARCHAR) - {parent_sql}
                FROM "{table}" WHERE "{column}" IS NOT NULL
            """).fetchall()
        ]
        if len(found) != 1 or found[0] < 1:
            msg = (
                f"level {n} ({column!r}) codes add {sorted(found)} characters to "
                "their parent's; without a delimiter each level needs one width"
            )
            raise ValueError(msg)
        widths.append(found[0])
        parent_sql = f'length("{column}"::VARCHAR)'
    min_width = widths[0] if len(set(widths)) == 1 else tuple(widths)
    return CodeFormat(root_code=root_code, delimiter="", min_width=min_width)


def _detect_delimiter(codes: list[str], code_column: str) -> str:
    """Find the single non-alphanumeric character common to every sampled code."""
    candidates: set[str] | None = None
    for code in codes:
        non_alnum = {c for c in code if not c.isalnum()}
        candidates = non_alnum if candidates is None else candidates & non_alnum
    if not candidates or len(candidates) != 1:
        msg = (
            f"could not infer a single recurring delimiter from {code_column!r}'s "
            f"existing values: {code_column!r} may not be a formatted hierarchical "
            f"code column"
        )
        raise ValueError(msg)
    return next(iter(candidates))


def _detect_root(codes: list[str], delimiter: str, code_column: str) -> str:
    """Find the shared first delimiter-split component across every sampled code."""
    roots = {code.split(delimiter)[0] for code in codes}
    if len(roots) != 1:
        msg = (
            f"{code_column!r} does not share one constant root component "
            f"(found {sorted(roots)}); it may not be this dataset's own "
            f"root-anchored hierarchy column"
        )
        raise ValueError(msg)
    return next(iter(roots))


def _detect_min_width(codes: list[str], delimiter: str, code_column: str) -> MinWidth:
    """Take each level's most common component width; one int if all levels agree."""
    by_level: list[Counter] = []
    for code in codes:
        for i, part in enumerate(code.split(delimiter)[1:]):
            if i == len(by_level):
                by_level.append(Counter())
            by_level[i][len(part)] += 1
    if not by_level:
        msg = f"no delimited components found in {code_column!r} to measure width from"
        raise ValueError(msg)
    widths = tuple(counts.most_common(1)[0][0] for counts in by_level)
    return widths[0] if len(set(widths)) == 1 else widths
