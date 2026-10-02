"""Runs every code check against `{name}_02`, one row per finding, per unit."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from topo_tools.core.code_detect._constants import (
    FORMAT_MIN_CODES,
    PREFIX_SHARE,
    SHAPE_SHARE,
)

logger = getLogger(__name__)

_COLUMNS = (
    "kind VARCHAR, level INTEGER, column_name VARCHAR, code_a VARCHAR, "
    "name_a VARCHAR, code_b VARCHAR, name_b VARCHAR, reason VARCHAR"
)


def _codes(source: str) -> str:
    """Each level's distinct (code, parent code) pairs, with their row count."""
    return f"""(
        SELECT level, code_column, code, parent_code, sum(row_count) AS row_count
        FROM "{source}" WHERE code IS NOT NULL AND name_index = 0 GROUP BY ALL
    )"""


def _named(source: str) -> str:
    return (
        f"""(SELECT * FROM "{source}" """
        "WHERE code IS NOT NULL AND name IS NOT NULL AND trim(name) <> '')"
    )


def _blank_code(source: str) -> str:
    return f"""--sql
        SELECT 'blank-code', level, code_column, NULL, NULL, NULL, NULL,
               printf('%d units under %s have no code: %s', count(*),
                      coalesce(parent_code, 'the root'),
                      coalesce(string_agg(DISTINCT name, ' / '), 'no name either'))
        FROM "{source}" WHERE code IS NULL AND name_index = 0
        GROUP BY level, code_column, parent_code
    """


def _conflict(source: str) -> str:
    return f"""--sql
        SELECT 'name-conflict', level, name_column, code, names[1], code, names[2],
               printf('code %s has %d names: %s', code, len(names),
                      array_to_string(names, ' / '))
        FROM (
            SELECT level, name_column, name_index, code,
                   list_sort(list(DISTINCT name)) AS names
            FROM {_named(source)} GROUP BY ALL
        )
        WHERE len(names) > 1
        QUALIFY row_number() OVER (PARTITION BY level, code ORDER BY name_index) = 1
    """


def _duplicate(source: str) -> str:
    return f"""--sql
        SELECT 'duplicate-code', level, code_column, code, NULL, NULL, NULL,
               printf('code %s is on %d features', code, sum(row_count)::INT)
        FROM {_codes(source)}
        WHERE level = (SELECT max(level) FROM "{source}")
        GROUP BY level, code_column, code HAVING sum(row_count) > 1
    """


def _prefix(source: str) -> str:
    return f"""--sql
        WITH pairs AS (
            SELECT * FROM {_codes(source)} WHERE parent_code IS NOT NULL
        ), levels AS (
            SELECT level FROM pairs GROUP BY level
            HAVING count(*) >= {FORMAT_MIN_CODES}
               AND avg(starts_with(code, parent_code)::INT) >= {PREFIX_SHARE}
        )
        SELECT 'prefix-mismatch', level, code_column, code, NULL, parent_code, NULL,
               printf('code %s does not start with its parent code %s',
                      code, parent_code)
        FROM pairs SEMI JOIN levels USING (level)
        WHERE NOT starts_with(code, parent_code)
    """


def _shapes(source: str) -> str:
    """Each level's distinct codes, every letter as A and digit as 9."""
    return f"""--sql
        SELECT DISTINCT level, code_column, code,
               regexp_replace(regexp_replace(code, '\\p{{L}}', 'A', 'g'),
                              '[0-9]', '9', 'g') AS shape
        FROM {_codes(source)}
    """


def _shape_shares(source: str) -> str:
    return f"""--sql
        WITH s AS ({_shapes(source)}), usual AS (
            SELECT level, mode(shape) AS usual, count(*) AS total
            FROM s GROUP BY level HAVING count(*) >= {FORMAT_MIN_CODES}
        )
        SELECT level, usual, total, count(*) FILTER (WHERE shape = usual) AS n
        FROM s JOIN usual USING (level) GROUP BY ALL
    """


def _format_outlier(source: str) -> str:
    return f"""--sql
        SELECT 'format-outlier', s.level, s.code_column, s.code, NULL, NULL, NULL,
               printf('code %s is shaped %s, unlike %d of %d level %d codes (%s)',
                      s.code, s.shape, u.n, u.total, s.level, u.usual)
        FROM ({_shapes(source)}) s JOIN ({_shape_shares(source)}) u USING (level)
        WHERE u.n >= u.total * {SHAPE_SHARE} AND s.shape <> u.usual
    """


def _format_undetected(source: str) -> str:
    return f"""--sql
        SELECT DISTINCT 'format-undetected', s.level, s.code_column, NULL, NULL,
               NULL, NULL,
               printf('level %d codes share no common shape: the most common, '
                      '%s, covers %d of %d', s.level, u.usual, u.n, u.total)
        FROM ({_shapes(source)}) s JOIN ({_shape_shares(source)}) u USING (level)
        WHERE u.n < u.total * {SHAPE_SHARE}
    """


_CHECKS = {
    "blank-code": _blank_code,
    "name-conflict": _conflict,
    "duplicate-code": _duplicate,
    "prefix-mismatch": _prefix,
    "format-outlier": _format_outlier,
    "format-undetected": _format_undetected,
}


def main(conn: DuckDBPyConnection, name: str, *, debug: bool = False) -> None:
    """Write `{name}_03`: every finding, one row per unit (or unit pair)."""
    source = f"{name}_02"
    tmps = []
    for i, (kind, build) in enumerate(_CHECKS.items(), start=1):
        tmp = f"{name}_03_tmp{i}"
        tmps.append(tmp)
        try:
            conn.execute(f'CREATE OR REPLACE TABLE "{tmp}" ({_COLUMNS})')
            conn.execute(f'INSERT INTO "{tmp}" {build(source)}')
        except Exception as e:  # noqa: BLE001 (one failing check must not hide the rest)
            logger.warning("%s check failed (%s); reporting none", kind, e)
            conn.execute(f'CREATE OR REPLACE TABLE "{tmp}" ({_COLUMNS})')
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_03" AS
        {" UNION ALL ".join(f'SELECT * FROM "{t}"' for t in tmps)}
    """)
    if not debug:
        for tmp in tmps:
            conn.execute(f'DROP TABLE IF EXISTS "{tmp}"')
