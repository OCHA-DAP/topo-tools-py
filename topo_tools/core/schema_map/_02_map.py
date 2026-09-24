"""Structurally discovers a source file's admin hierarchy and code/name roles.

See docs/explanation/schema_map.md and docs/adr/0054, 0064-0066 for the
algorithm and why.
"""

import re
from dataclasses import dataclass
from logging import getLogger

from duckdb import DuckDBPyConnection

from topo_tools.core.admin_columns import sibling_name
from topo_tools.core.constants import (
    is_floating_duckdb_type,
    is_noise_column,
    is_temporal_duckdb_type,
)
from topo_tools.core.duckdb_utils import quote_identifier
from topo_tools.core.schema_map._constants import (
    CONFIDENCE_AMBIGUOUS,
    CONFIDENCE_SUPPLEMENTAL,
)
from topo_tools.core.schema_map._target_schema import TargetSchema

logger = getLogger(__name__)

# fid/geom/source_file are topo-tools' own internal columns, never candidate
# source data (source_file is added by core.assign, dropped only at final export).
_EXCLUDED_COLUMNS = {"fid", "geom", "source_file"}

_CODE_SHAPE_MAJORITY = 0.5

# A same-role bracket winner above this collapse ratio is a coarser
# grouping (ADR-0065), not a same-level translation variant (ADR-0076).
_WINNER_MAX_COLLAPSE_RATIO = 0.30


@dataclass
class _Row:
    source_column: str | None
    target_column: str | None
    note: str
    role: str | None = None  # "code" or "name", for output ordering
    level: int | None = None
    unique_count: int | None = None


def _candidate_columns(conn: DuckDBPyConnection, table: str) -> list[str]:
    """List columns eligible for hierarchy detection, of any type."""
    rows = conn.execute(f'DESCRIBE "{table}"').fetchall()
    return [
        r[0]
        for r in rows
        if r[0] not in _EXCLUDED_COLUMNS and not is_noise_column(r[0])
    ]


def _distinct_counts(
    conn: DuckDBPyConnection, table: str, columns: list[str]
) -> dict[str, int]:
    """One query, COUNT(DISTINCT) for every column, keyed by column name."""
    if not columns:
        return {}
    select = ", ".join(f"COUNT(DISTINCT {quote_identifier(c)})" for c in columns)
    result = conn.execute(f"SELECT {select} FROM {quote_identifier(table)}").fetchone()
    return dict(zip(columns, result, strict=True))


def _temporal_columns(
    conn: DuckDBPyConnection, table: str, columns: list[str]
) -> set[str]:
    """Every `columns` member whose DuckDB type is a date/time one."""
    rows = conn.execute(f"DESCRIBE {quote_identifier(table)}").fetchall()
    types = {c: t for c, t, *_ in rows}
    return {c for c in columns if is_temporal_duckdb_type(types[c])}


_MIN_ROWS_FOR_SPATIAL_COHERENCE = 10
_MIN_SPATIAL_R2 = 0.7


def _has_geometry_column(conn: DuckDBPyConnection, table: str) -> bool:
    """Check `table` has a `geom` column at all; not every caller loads one."""
    rows = conn.execute(f"DESCRIBE {quote_identifier(table)}").fetchall()
    return any(r[0] == "geom" for r in rows)


def _spatially_coherent(conn: DuckDBPyConnection, table: str, column: str) -> bool:
    """Check column's own groups explain most of the file's centroid spread.

    Too little evidence (row count or spatial spread) is not evidence against.
    """
    row = conn.execute(f"""--sql
        WITH pts AS (
            SELECT {quote_identifier(column)} AS g,
                ST_X(ST_Centroid(geom)) AS cx, ST_Y(ST_Centroid(geom)) AS cy
            FROM {quote_identifier(table)}
            WHERE {quote_identifier(column)} IS NOT NULL
        ),
        per_group AS (
            SELECT g, COUNT(*) AS n, VAR_POP(cx) AS vx, VAR_POP(cy) AS vy
            FROM pts GROUP BY g
        )
        SELECT
            SUM(n),
            SUM(n * COALESCE(vx, 0)) / SUM(n), SUM(n * COALESCE(vy, 0)) / SUM(n),
            (SELECT VAR_POP(cx) FROM pts), (SELECT VAR_POP(cy) FROM pts)
        FROM per_group
        HAVING COUNT(*) >= 2
    """).fetchone()
    if row is None:
        return True
    total_rows, within_x, within_y, total_x, total_y = row
    if total_rows < _MIN_ROWS_FOR_SPATIAL_COHERENCE:
        return True
    total = (total_x or 0) + (total_y or 0)
    if total == 0:
        return True
    within = (within_x or 0) + (within_y or 0)
    return 1 - within / total >= _MIN_SPATIAL_R2


def _embeds(
    conn: DuckDBPyConnection,
    table: str,
    child: str,
    parent: str,
    *,
    has_geom: bool = False,
) -> bool:
    """Check every non-null row has `child` contain `parent`, tolerating one sentinel.

    The tolerance itself is trusted only if `child` is also spatially coherent.
    """
    evaluated_where = f"""
        {quote_identifier(child)} IS NOT NULL AND {quote_identifier(parent)} IS NOT NULL
    """
    not_contains = f"""
        NOT contains(
            CAST({quote_identifier(child)} AS VARCHAR),
            CAST({quote_identifier(parent)} AS VARCHAR)
        )
    """
    evaluated, bad = conn.execute(f"""--sql
        SELECT
            COUNT(*) FILTER (WHERE {evaluated_where}),
            COUNT(*) FILTER (WHERE {evaluated_where} AND {not_contains})
        FROM {quote_identifier(table)}
    """).fetchone()
    if bad == 0:
        return evaluated > 0
    culprits = conn.execute(f"""--sql
        SELECT DISTINCT CAST({quote_identifier(child)} AS VARCHAR)
        FROM {quote_identifier(table)}
        WHERE {evaluated_where} AND {not_contains}
    """).fetchall()
    if len(culprits) != 1:
        return False
    remaining = conn.execute(
        f"""--sql
        SELECT COUNT(*) FROM {quote_identifier(table)}
        WHERE {evaluated_where}
          AND CAST({quote_identifier(child)} AS VARCHAR) != ?
        """,
        [culprits[0][0]],
    ).fetchone()[0]
    if remaining <= 0:
        return False
    return not has_geom or _spatially_coherent(conn, table, child)


def _looks_code_shaped(conn: DuckDBPyConnection, table: str, column: str) -> bool:
    """Check whether most non-null values contain a digit.

    Never true for a date/time column; only consulted absent embedding evidence.
    """
    rows = conn.execute(f"DESCRIBE {quote_identifier(table)}").fetchall()
    column_type = next(t for c, t, *_ in rows if c == column)
    if is_temporal_duckdb_type(column_type):
        return False
    digits, total = conn.execute(f"""--sql
        SELECT
            COUNT(*) FILTER (
                WHERE regexp_matches(
                    CAST({quote_identifier(column)} AS VARCHAR), '[0-9]'
                )
            ),
            COUNT(*) FILTER (WHERE {quote_identifier(column)} IS NOT NULL)
        FROM {quote_identifier(table)}
    """).fetchone()
    return total > 0 and digits / total > _CODE_SHAPE_MAJORITY


_MIN_GROUPS_FOR_TOLERANCE = 2


def _containment_holds(
    conn: DuckDBPyConnection, table: str, coarser: str, finer: str
) -> bool:
    """Check every non-null `finer` maps to a single non-null `coarser`, mostly."""
    coarser_id = quote_identifier(coarser)
    groups = conn.execute(f"""--sql
        SELECT COUNT(DISTINCT {coarser_id}) AS coarser_count,
               COUNT(*) FILTER (WHERE {coarser_id} IS NULL) AS null_coarser
        FROM {quote_identifier(table)}
        WHERE {quote_identifier(finer)} IS NOT NULL
        GROUP BY {quote_identifier(finer)}
    """).fetchall()
    violators = sum(
        1
        for coarser_count, null_coarser in groups
        if coarser_count > 1 or null_coarser > 0
    )
    tolerance = 1 if len(groups) > _MIN_GROUPS_FOR_TOLERANCE else 0
    return violators <= tolerance


_MIN_GROUPS_FOR_STRICT_CONTAINMENT = 10
_MIN_FINEST_UNIQUENESS_RATIO = 0.9


def _containment_perfect(
    conn: DuckDBPyConnection, table: str, coarser: str, finer: str
) -> bool:
    """Check every non-null `finer` maps to exactly one non-null `coarser`."""
    coarser_id = quote_identifier(coarser)
    groups = conn.execute(f"""--sql
        SELECT COUNT(DISTINCT {coarser_id}) AS coarser_count,
               COUNT(*) FILTER (WHERE {coarser_id} IS NULL) AS null_coarser
        FROM {quote_identifier(table)}
        WHERE {quote_identifier(finer)} IS NOT NULL
        GROUP BY {quote_identifier(finer)}
    """).fetchall()
    if len(groups) < _MIN_GROUPS_FOR_STRICT_CONTAINMENT:
        return False
    return all(
        coarser_count == 1 and null_coarser == 0
        for coarser_count, null_coarser in groups
    )


def _is_near_row_unique(conn: DuckDBPyConnection, table: str, column: str) -> bool:
    """Check column's own distinct count nearly matches the table's row count."""
    total, distinct = conn.execute(f"""--sql
        SELECT COUNT(*), COUNT(DISTINCT {quote_identifier(column)})
        FROM {quote_identifier(table)}
    """).fetchone()
    return total > 0 and distinct / total >= _MIN_FINEST_UNIQUENESS_RATIO


_MIN_JOINT_EVIDENCE_FOR_BIJECTION = 2
_MIN_ROOT_EVIDENCE_COLUMNS = 2
_LEVEL_DIGIT_RE = re.compile(r"\d+")


def _same_naming_digit(a: str, b: str) -> bool:
    """Check a and b share an actual naming digit; neither having one doesn't count."""
    match_a, match_b = _LEVEL_DIGIT_RE.search(a), _LEVEL_DIGIT_RE.search(b)
    return (
        match_a is not None
        and match_b is not None
        and match_a.group() == match_b.group()
    )


def _companion_holds(conn: DuckDBPyConnection, table: str, x: str, y: str) -> bool:
    """Check x determines y on rows where both are populated, ignoring the rest."""
    groups = conn.execute(f"""--sql
        SELECT COUNT(DISTINCT {quote_identifier(y)}) AS y_count
        FROM {quote_identifier(table)}
        WHERE {quote_identifier(x)} IS NOT NULL AND {quote_identifier(y)} IS NOT NULL
        GROUP BY {quote_identifier(x)}
    """).fetchall()
    violators = sum(1 for (y_count,) in groups if y_count > 1)
    tolerance = 1 if len(groups) > _MIN_GROUPS_FOR_TOLERANCE else 0
    return violators <= tolerance


def _bijective(conn: DuckDBPyConnection, table: str, a: str, b: str) -> bool:
    """Check a and b correspond 1:1, using the joint subset only if both are sparse."""
    joint = conn.execute(f"""--sql
        SELECT COUNT(*) FROM {quote_identifier(table)}
        WHERE {quote_identifier(a)} IS NOT NULL AND {quote_identifier(b)} IS NOT NULL
    """).fetchone()[0]
    if joint < _MIN_JOINT_EVIDENCE_FOR_BIJECTION and not _same_naming_digit(a, b):
        return False
    if _fully_populated(conn, table, a) or _fully_populated(conn, table, b):
        return _containment_holds(conn, table, a, b) and _containment_holds(
            conn, table, b, a
        )
    return _companion_holds(conn, table, a, b) and _companion_holds(conn, table, b, a)


def _combined_distinct_count(
    conn: DuckDBPyConnection, table: str, parent: str, column: str
) -> int:
    """COUNT(DISTINCT (parent, column)), catching a value reused across parents."""
    return conn.execute(f"""--sql
        SELECT COUNT(*) FROM (
            SELECT DISTINCT {quote_identifier(parent)}, {quote_identifier(column)}
            FROM {quote_identifier(table)}
        )
    """).fetchone()[0]


def _build_level_groups(
    conn: DuckDBPyConnection, table: str, columns: list[str], counts: dict[str, int]
) -> list[tuple[int, list[str]]]:
    """Group every column (code or name alike) by bijection, count picks the label."""
    groups = [
        (max(counts[c] for c in cluster), cluster)
        for cluster in _cluster_by_bijection(conn, table, columns, counts)
    ]
    groups.sort(key=lambda g: g[0])
    return groups


def _cluster_by_bijection(
    conn: DuckDBPyConnection, table: str, cols: list[str], counts: dict[str, int]
) -> list[list[str]]:
    """Union bijective columns, cross-count only if either side is NULL-sparse."""
    fully_populated = {c: _fully_populated(conn, table, c) for c in cols}
    parent = {c: c for c in cols}

    def find(c: str) -> str:
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    for i, a in enumerate(cols):
        for b in cols[i + 1 :]:
            both_dense = fully_populated[a] and fully_populated[b]
            comparable = (both_dense and counts[a] == counts[b]) or (
                not both_dense and _same_naming_digit(a, b)
            )
            if comparable and _bijective(conn, table, a, b):
                parent[find(a)] = find(b)

    clusters: dict[str, list[str]] = {}
    for c in cols:
        clusters.setdefault(find(c), []).append(c)
    return list(clusters.values())


def _order_groups_by_containment(
    conn: DuckDBPyConnection, table: str, groups: list[tuple[int, list[str]]]
) -> list[tuple[int, list[str]]]:
    """Order groups coarsest-first by containment, not raw COUNT(DISTINCT)."""
    n = len(groups)
    joins = [[False] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            joins[i][j] = all(
                _containment_holds(conn, table, coarser=a, finer=b)
                for a in groups[i][1]
                for b in groups[j][1]
            )

    indegree = [sum(joins[k][i] for k in range(n)) for i in range(n)]
    remaining = set(range(n))
    order: list[int] = []
    while remaining:
        ready = [i for i in remaining if indegree[i] == 0] or list(remaining)
        i = min(ready, key=lambda i: (groups[i][0], groups[i][1]))
        order.append(i)
        remaining.discard(i)
        for j in remaining:
            if joins[i][j]:
                indegree[j] -= 1
    return [groups[i] for i in order]


def _non_floating(
    conn: DuckDBPyConnection, table: str, columns: list[str]
) -> list[str]:
    """Non-floating members of columns; an all-floating group has none, no fallback."""
    rows = conn.execute(f"DESCRIBE {quote_identifier(table)}").fetchall()
    types = {r[0]: r[1] for r in rows}
    return [c for c in columns if not is_floating_duckdb_type(types[c])]


def _embed_witnesses(
    conn: DuckDBPyConnection, table: str, columns: list[str]
) -> list[str]:
    """Non-floating members only: a fraction's digits satisfy `_embeds()` by chance."""
    witnesses = _non_floating(conn, table, columns)
    return witnesses or columns


def _build_edges(
    conn: DuckDBPyConnection, table: str, groups: list[tuple[int, list[str]]]
) -> dict[tuple[int, int], tuple[bool, bool, bool]]:
    """Every coarser/finer pair's (containment holds, embeds, perfect+row-unique)."""
    has_geom = _has_geometry_column(conn, table)
    edges: dict[tuple[int, int], tuple[bool, bool, bool]] = {}
    for finer_idx, (_finer_count, finer_cols) in enumerate(groups):
        finer_witnesses = _embed_witnesses(conn, table, finer_cols)
        finer_strict = _non_floating(conn, table, finer_cols)
        finer_near_unique = any(
            _is_near_row_unique(conn, table, c) for c in finer_strict
        )
        for coarser_idx in range(finer_idx):
            _coarser_count, coarser_cols = groups[coarser_idx]
            coarser_witnesses = _embed_witnesses(conn, table, coarser_cols)
            coarser_strict = _non_floating(conn, table, coarser_cols)
            joins = all(
                _containment_holds(conn, table, coarser=a, finer=b)
                for a in coarser_cols
                for b in finer_cols
            )
            embeds = joins and any(
                _embeds(conn, table, b, a, has_geom=has_geom)
                for a in coarser_witnesses
                for b in finer_witnesses
            )
            strong = (
                joins
                and not embeds
                and finer_near_unique
                and any(
                    _containment_perfect(conn, table, coarser=a, finer=b)
                    for a in coarser_strict
                    for b in finer_strict
                )
            )
            edges[coarser_idx, finer_idx] = (joins, embeds, strong)
    return edges


def _group_digit(cols: list[str]) -> int | None:
    """Return the single naming digit every column in a group agrees on."""
    digits = {
        int(m.group()) for c in cols if (m := _LEVEL_DIGIT_RE.search(c)) is not None
    }
    return digits.pop() if len(digits) == 1 else None


def _bridged_edges(
    groups: list[tuple[int, list[str]]],
    edges: dict[tuple[int, int], tuple[bool, bool, bool]],
) -> set[tuple[int, int]]:
    """Edges bracketing a level whose digit sits exactly between its neighbors'.

    A verified direct skip across it (its own coarser to its own finer) then
    needs no embedding of its own, e.g. a name-only adm2 between adm1/adm3.
    """
    n = len(groups)
    digits = [_group_digit(cols) for _count, cols in groups]
    bridged: set[tuple[int, int]] = set()
    for k in range(n):
        if digits[k] is None:
            continue
        for c in range(k):
            if digits[c] is None or digits[c] >= digits[k] or not edges[c, k][0]:
                continue
            for f in range(k + 1, n):
                if digits[f] is None or digits[k] >= digits[f]:
                    continue
                if edges[k, f][0] and edges[c, f][1]:
                    bridged.add((c, k))
                    bridged.add((k, f))
    return bridged


def _build_chain(
    conn: DuckDBPyConnection, table: str, groups: list[tuple[int, list[str]]]
) -> list[tuple[int, list[str]]]:
    """Longest nesting path; a non-constant edge must be embedding-justified.

    See docs/adr/0066: a constant needs no embedding, anything else does,
    unless no candidate pair in the whole file embeds at all (docs/adr/0070).
    """
    n = len(groups)
    has_geom = _has_geometry_column(conn, table)
    edges = _build_edges(conn, table, groups)
    no_embedding_anywhere = not any(
        embeds for _joins, embeds, _strong in edges.values()
    )
    bridged_edges = _bridged_edges(groups, edges)

    # Only an unbroken, fully-populated constant prefix from index 0 is the
    # genuine root; a sparse column can coincidentally have one distinct value.
    in_root_prefix = [False] * n
    still_root = True
    for idx in range(n):
        in_root_prefix[idx] = (
            still_root
            and groups[idx][0] == 1
            and all(_fully_populated(conn, table, c) for c in groups[idx][1])
        )
        still_root = in_root_prefix[idx]

    group_code_shaped = [
        any(_looks_code_shaped(conn, table, c) for c in cols) for _count, cols in groups
    ]

    best_len = [1] * n
    best_prev: list[int | None] = [None] * n
    chain_has_embed = [False] * n
    for finer_idx in range(n):
        for coarser_idx in range(finer_idx):
            joins, embeds, strong = edges[coarser_idx, finer_idx]
            if not joins:
                continue
            # A coincidentally-constant, non-root column can't extend a chain.
            if groups[coarser_idx][0] == 1 and not in_root_prefix[coarser_idx]:
                continue
            # The root's own freebie is trusted unconditionally only without
            # geometry; with it, an ungrounded finer group must corroborate.
            root_freebie = in_root_prefix[coarser_idx] and (
                embeds
                or not has_geom
                or any(
                    _spatially_coherent(conn, table, c) for c in groups[finer_idx][1]
                )
            )
            justified = (
                root_freebie
                or embeds
                or (strong and chain_has_embed[coarser_idx])
                or no_embedding_anywhere
                or (coarser_idx, finer_idx) in bridged_edges
            )
            if not justified:
                continue
            candidate_len = best_len[coarser_idx] + 1
            prev = best_prev[finer_idx]
            # On a tie, a code-shaped sibling outranks a name-shaped one.
            better = candidate_len > best_len[finer_idx] or (
                candidate_len == best_len[finer_idx]
                and prev is not None
                and group_code_shaped[coarser_idx]
                and not group_code_shaped[prev]
            )
            if better:
                best_len[finer_idx] = candidate_len
                best_prev[finer_idx] = coarser_idx
                chain_has_embed[finer_idx] = embeds or chain_has_embed[coarser_idx]
    if n == 0:
        return []
    end = max(range(n), key=lambda i: (best_len[i], len(groups[i][1]), groups[i][0]))
    chain_indices = []
    i: int | None = end
    while i is not None:
        chain_indices.append(i)
        i = best_prev[i]
    chain_indices.reverse()
    return [groups[i] for i in chain_indices]


def _numbered_target(template: str, level: int, index: int) -> str:
    """Render a level's template, suffixing the 2nd+ same-level column 1, 2, ..."""
    rendered = template.format(n=level)
    return rendered if index == 0 else sibling_name(rendered, index)


def _bracket_index(code_counts: list[int], count: int) -> int | None:
    """Find the sole chain index k where code_counts[k-1] < count <= code_counts[k]."""
    lower = 0
    for index, upper in enumerate(code_counts):
        if lower < count <= upper:
            return index
        lower = upper
    return None


def _fully_populated(conn: DuckDBPyConnection, table: str, column: str) -> bool:
    """Check `column` is non-null everywhere (a real constant, not a sparse one)."""
    total, populated = conn.execute(f"""--sql
        SELECT COUNT(*), COUNT({quote_identifier(column)})
        FROM {quote_identifier(table)}
    """).fetchone()
    return total == populated


def _assign_chain_roles(  # noqa: PLR0913, PLR0917
    conn: DuckDBPyConnection,
    table: str,
    chain: list[tuple[int, list[str]]],
    schema: TargetSchema,
    counts: dict[str, int],
    offset: int = 0,
) -> dict[str, "_Row"]:
    """Assign every chain-level column a code/name role and numbered target.

    Embeds the resolved parent, or looks code-shaped -> code; else -> name.
    """
    rows: dict[str, _Row] = {}
    for index, (count, cols) in enumerate(chain):
        # A constant root folds away with no deeper level, or a fully-populated
        # one; a root above a partial deeper level is the only depth evidence.
        next_fully_populated = len(chain) > 1 and all(
            _fully_populated(conn, table, c) for c in chain[1][1]
        )
        is_foldable_root = (
            index == 0 and count == 1 and (len(chain) == 1 or next_fully_populated)
        )
        if is_foldable_root and _fully_populated(conn, table, cols[0]):
            continue
        level = index + offset
        parent_cols = chain[index - 1][1] if index > 0 else []
        embeds_parent = {
            c: any(_embeds(conn, table, c, p) for p in parent_cols) for c in cols
        }
        roles: dict[str, str] = {
            c: "code"
            if embeds_parent[c] or _looks_code_shaped(conn, table, c)
            else "name"
            for c in cols
        }
        parent_code = parent_cols[0] if parent_cols else None
        for role, template in (
            ("code", schema.code_field),
            ("name", schema.name_field),
        ):
            members = [c for c in cols if roles[c] == role]
            for member_index, column in enumerate(members):
                target = _numbered_target(template, level, member_index)
                unique_count = (
                    counts[column]
                    if parent_code is None
                    else _combined_distinct_count(conn, table, parent_code, column)
                )
                rows[column] = _Row(
                    column,
                    target,
                    "",
                    role=role,
                    level=level,
                    unique_count=unique_count,
                )
    return rows


def _collapse_ratio(
    counts: dict[str, int], column: str, level_unit_count: int
) -> float:
    """Fraction of a level's own units a winning candidate's values collapse away."""
    return 1 - counts[column] / level_unit_count


def _bracket_level(  # noqa: PLR0913, PLR0917
    conn: DuckDBPyConnection,
    table: str,
    chain: list[tuple[int, list[str]]],
    level: int,
    candidates: list[str],
    counts: dict[str, int],
    schema: TargetSchema,
    chain_rows: dict[str, "_Row"],
    offset: int = 0,
) -> dict[str, "_Row"]:
    """Resolve one bracketed level's candidates into name/supplemental/ambiguous rows.

    A winner is `name` unless the level already has one and the winner's own
    collapse ratio exceeds `_WINNER_MAX_COLLAPSE_RATIO` (docs/adr/0076).
    """
    level_count, level_cols = chain[level]
    code_column = level_cols[0]
    winners = {
        c
        for c in candidates
        if _containment_holds(conn, table, coarser=c, finer=code_column)
    }
    existing_name_members = [
        m for m in level_cols if m in chain_rows and chain_rows[m].role == "name"
    ]
    level_has_name = bool(existing_name_members)
    parent_code_column = chain[level - 1][1][0] if level > 0 else None

    def unique_count_for(column: str) -> int:
        if parent_code_column is None:
            return counts[column]
        return _combined_distinct_count(conn, table, parent_code_column, column)

    rows: dict[str, _Row] = {}
    winner_index = len(existing_name_members)
    level_n = level + offset
    for column in candidates:
        unique_count = unique_count_for(column)
        if column not in winners:
            rows[column] = _Row(
                column,
                None,
                f"{CONFIDENCE_AMBIGUOUS}, level {level_n}",
                level=level_n,
                unique_count=unique_count,
            )
        elif (
            level_has_name
            and _collapse_ratio(counts, column, level_count)
            > _WINNER_MAX_COLLAPSE_RATIO
        ):
            rows[column] = _Row(
                column,
                None,
                f"{CONFIDENCE_SUPPLEMENTAL}, superset of level {level_n}",
                level=level_n,
                unique_count=unique_count,
            )
        else:
            target = _numbered_target(schema.name_field, level_n, winner_index)
            winner_index += 1
            rows[column] = _Row(
                column,
                target,
                "",
                role="name",
                level=level_n,
                unique_count=unique_count,
            )
    return rows


def _bracket_other_columns(  # noqa: PLR0913, PLR0917
    conn: DuckDBPyConnection,
    table: str,
    chain: list[tuple[int, list[str]]],
    other_columns: list[str],
    counts: dict[str, int],
    schema: TargetSchema,
    chain_rows: dict[str, "_Row"],
    offset: int = 0,
) -> dict[str, "_Row"]:
    """Bracket non-chain columns into the chain by cardinality range."""
    code_counts = [count for count, _cols in chain]
    bracketed: dict[int, list[str]] = {}
    for column in other_columns:
        index = _bracket_index(code_counts, counts[column])
        if index is not None:
            bracketed.setdefault(index, []).append(column)

    rows: dict[str, _Row] = {}
    for level, candidates in bracketed.items():
        if chain[level][0] == 1:
            continue
        rows.update(
            _bracket_level(
                conn,
                table,
                chain,
                level,
                candidates,
                counts,
                schema,
                chain_rows,
                offset,
            )
        )
    return rows


def resolve_columns(
    conn: DuckDBPyConnection,
    table: str,
    schema: TargetSchema,
    level: int | None = None,
    *,
    implied_country: bool = False,
) -> dict[str, _Row]:
    """Resolve every candidate column to a level/role; `schema` only renders names.

    `level` anchors the finest level; else `implied_country` numbers a varying root 1.
    """
    columns = _candidate_columns(conn, table)
    counts = _distinct_counts(conn, table, columns)

    # An all-null column has no evidence either way, same principle as _embeds();
    # a date/time column is categorically never an admin identity column.
    temporal_columns = _temporal_columns(conn, table, columns)
    chainable_columns = [
        c for c in columns if counts[c] > 0 and c not in temporal_columns
    ]
    level_groups = _build_level_groups(conn, table, chainable_columns, counts)
    level_groups = _order_groups_by_containment(conn, table, level_groups)
    chain = _build_chain(conn, table, level_groups)
    # A lone level with a lone column has no parent to embed and no sibling
    # to pair with, indistinguishable from an arbitrary non-hierarchy column.
    if len(chain) == 1 and len(chain[0][1]) < _MIN_ROOT_EVIDENCE_COLUMNS:
        chain = []

    if not chain:
        offset = 0
    elif level is not None:
        offset = level - (len(chain) - 1)
    elif implied_country and chain[0][0] > 1:
        offset = 1
        logger.warning(
            "no single-value country column; numbered the coarsest level 1 "
            "assuming one country above the file, pass --level N if the file "
            "spans multiple countries or lacks its coarser levels"
        )
    else:
        offset = 0
    rows = _assign_chain_roles(conn, table, chain, schema, counts, offset)
    lowest = min((r.level for r in rows.values() if r.level is not None), default=0)
    if lowest < 0:
        msg = (
            f"level={level} is too shallow: found {len(chain)} nested levels, "
            f"so the coarsest would be {lowest}"
        )
        raise ValueError(msg)

    chained_columns = {c for _count, cols in chain for c in cols}
    other_columns = [c for c in columns if c not in chained_columns]

    other_rows = _bracket_other_columns(
        conn, table, chain, other_columns, counts, schema, rows, offset
    )
    rows.update(other_rows)

    for column in columns:
        if column not in rows:
            rows[column] = _Row(column, None, "", unique_count=counts[column])
    return rows


def main(
    conn: DuckDBPyConnection,
    name: str,
    schema: TargetSchema,
    level: int | None = None,
) -> None:
    """Discover a source file's admin hierarchy, writing crosswalk `{name}_02`."""
    table = f"{name}_01"
    columns = _candidate_columns(conn, table)
    rows = resolve_columns(conn, table, schema, level, implied_country=True)

    def sort_key(row: _Row, source_position: int) -> tuple[int, int, int, int]:
        if row.level is None:
            return (1, 0, 0, source_position)
        role_priority = 0 if row.role == "name" else 1
        return (0, -row.level, role_priority, source_position)

    position = {c: i for i, c in enumerate(columns)}
    entries = [(rows[c], position[c]) for c in columns]
    entries.sort(key=lambda pair: sort_key(*pair))

    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "{name}_02" (
            column_order INTEGER, source_column VARCHAR, target_column VARCHAR,
            unique_count INTEGER, note VARCHAR
        )
    """)
    for i, (r, _pos) in enumerate(entries):
        conn.execute(
            f'INSERT INTO "{name}_02" VALUES (?, ?, ?, ?, ?)',
            [i, r.source_column, r.target_column, r.unique_count, r.note],
        )
