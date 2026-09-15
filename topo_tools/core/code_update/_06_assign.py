"""Applies the changelog-driven retention policy, one level at a time, ascending."""

from dataclasses import dataclass

from duckdb import DuckDBPyConnection

from topo_tools.core.code import CodeFormat, assign_new_codes, rewrite_child_code
from topo_tools.core.code_update._02_levels import SideLevels

_RETAIN_CLASSES = {"unchanged", "renamed"}
_SINGLE_PREDECESSOR_CLASSES = {"modified", "relocated"}
_RETIRE_ONLY_CLASSES = {"merge", "complex"}

_REASONS = {
    ("unchanged", "retained"): "geometry and identity unchanged, code retained",
    ("renamed", "retained"): "name changed, geometry unchanged, code retained",
    ("removed", "retired"): "no NEW counterpart, code retired",
    ("merge", "retired"): "merged into another unit, code retired",
    ("complex", "retired"): "involved in a complex N:M change, code retired",
    ("created", "new"): "new unit, no OLD counterpart",
    ("modified", "new"): "geometry modified past threshold, new code assigned",
    (
        "relocated",
        "new",
    ): "unit relocated, new code assigned under its re-derived parent",
    ("split", "new"): "split from predecessor, new code assigned",
    ("merge", "new"): "formed by merging OLD units, new code assigned",
    ("complex", "new"): "formed by a complex N:M change, new code assigned",
}


@dataclass
class ChangeRow:
    """One changelog row: an old/new code pair, or a one-sided created/removed row."""

    level: int
    old_code: str | None
    old_name: str | None
    new_code: str | None
    new_name: str | None
    relationship_class: str
    cluster_id: int
    match_method: str | None
    code_outcome: str
    reason: str
    predecessor_code: str | None
    b_fid: int | None


def _fetch_dict(
    conn: DuckDBPyConnection, table: str, key_col: str, val_col: str
) -> dict:
    rows = conn.execute(f'SELECT "{key_col}", "{val_col}" FROM "{table}"').fetchall()
    return dict(rows)


def _reduce_match_methods(
    pairs: list[tuple[int, int]], lookup: dict[tuple[int, int], str]
) -> str | None:
    """Collapse every linked pair's own match_method to one value, joined if mixed."""
    methods = {lookup[p] for p in pairs if p in lookup}
    return "+".join(sorted(methods)) if methods else None


def main(  # noqa: C901, PLR0912, PLR0915
    conn: DuckDBPyConnection,
    name: str,
    *,
    side_a: SideLevels,
    side_b: SideLevels,
    fmt: CodeFormat,
) -> tuple[dict[int, dict[int, str]], list[ChangeRow]]:
    """Return ({level: {new_fid: new_code}}, the full changelog), ascending."""
    levels = sorted(side_a.columns)
    new_code_by_fid: dict[int, dict[int, str]] = {}
    changelog: list[ChangeRow] = []

    for idx, n in enumerate(levels):
        code_col_a = side_a.columns[n]
        old_code_by_fid = _fetch_dict(conn, f"{name}_dsl_{n}_a", "fid", code_col_a)
        old_name_by_fid = (
            _fetch_dict(conn, f"{name}_dsl_{n}_a", "fid", side_a.names[n])
            if side_a.names[n]
            else {}
        )
        new_name_by_fid = (
            _fetch_dict(conn, f"{name}_dsl_{n}_b", "fid", side_b.names[n])
            if side_b.names[n]
            else {}
        )
        child_to_parent_fid = (
            _fetch_dict(
                conn, f"{name}_reparent_{n}_02_assign", "child_fid", "parent_fid"
            )
            if idx > 0
            else {}
        )

        def new_parent_code(
            b_fid: int,
            idx: int = idx,
            n: int = n,
            child_to_parent_fid: dict = child_to_parent_fid,
        ) -> str:
            if idx == 0:
                return fmt.root_code
            parent_fid = child_to_parent_fid.get(b_fid)
            if parent_fid is None:
                msg = f"level {n}: no re-derived parent for new fid {b_fid}"
                raise ValueError(msg)
            return new_code_by_fid[levels[idx - 1]][parent_fid]

        pair_method = {
            (a_fid, b_fid): match_method
            for a_fid, b_fid, match_method in conn.execute(f"""--sql
                SELECT a_fid, b_fid, match_method FROM "{name}_chg_{n}_03a"
            """).fetchall()
        }

        b_rows = conn.execute(f"""--sql
            SELECT side, fid, cluster_id, relationship_class
            FROM "{name}_chg_{n}_03b"
        """).fetchall()
        clusters: dict[int, dict] = {}
        for side, fid, cluster_id, relationship_class in b_rows:
            c = clusters.setdefault(
                cluster_id, {"a": [], "b": [], "class": relationship_class}
            )
            c["a" if side == "a" else "b"].append(fid)

        retained_codes: list[str] = []
        new_batch: list[tuple[str, str]] = []
        new_batch_meta: dict[str, dict] = {}
        level_new_codes: dict[int, str] = {}

        for cluster_id, c in clusters.items():
            rel, a_fids, b_fids = c["class"], c["a"], c["b"]

            if rel in _RETAIN_CLASSES:
                a_fid, b_fid = a_fids[0], b_fids[0]
                old_code = old_code_by_fid[a_fid]
                new_code = rewrite_child_code(old_code, new_parent_code(b_fid), fmt)
                level_new_codes[b_fid] = new_code
                retained_codes.append(new_code)
                changelog.append(
                    ChangeRow(
                        level=n,
                        old_code=old_code,
                        old_name=old_name_by_fid.get(a_fid),
                        new_code=new_code,
                        new_name=new_name_by_fid.get(b_fid),
                        relationship_class=rel,
                        cluster_id=cluster_id,
                        match_method=pair_method.get((a_fid, b_fid)),
                        code_outcome="retained",
                        reason=_REASONS[(rel, "retained")],
                        predecessor_code=None,
                        b_fid=b_fid,
                    )
                )
                continue

            if rel == "removed":
                changelog.extend(
                    ChangeRow(
                        level=n,
                        old_code=old_code_by_fid[a_fid],
                        old_name=old_name_by_fid.get(a_fid),
                        new_code=None,
                        new_name=None,
                        relationship_class=rel,
                        cluster_id=cluster_id,
                        match_method=None,
                        code_outcome="retired",
                        reason=_REASONS[(rel, "retired")],
                        predecessor_code=None,
                        b_fid=None,
                    )
                    for a_fid in a_fids
                )
                continue

            if rel in _RETIRE_ONLY_CLASSES:
                changelog.extend(
                    ChangeRow(
                        level=n,
                        old_code=old_code_by_fid[a_fid],
                        old_name=old_name_by_fid.get(a_fid),
                        new_code=None,
                        new_name=None,
                        relationship_class=rel,
                        cluster_id=cluster_id,
                        match_method=_reduce_match_methods(
                            [(a_fid, b) for b in b_fids], pair_method
                        ),
                        code_outcome="retired",
                        reason=_REASONS[(rel, "retired")],
                        predecessor_code=None,
                        b_fid=None,
                    )
                    for a_fid in a_fids
                )
                for b_fid in b_fids:
                    fid_key = f"n{n}_{b_fid}"
                    new_batch.append((fid_key, new_parent_code(b_fid)))
                    new_batch_meta[fid_key] = {
                        "b_fid": b_fid,
                        "old_code": None,
                        "old_name": None,
                        "predecessor": None,
                        "cluster_id": cluster_id,
                        "class": rel,
                        "match_method": _reduce_match_methods(
                            [(a, b_fid) for a in a_fids], pair_method
                        ),
                    }
                continue

            if rel == "created":
                b_fid = b_fids[0]
                fid_key = f"n{n}_{b_fid}"
                new_batch.append((fid_key, new_parent_code(b_fid)))
                new_batch_meta[fid_key] = {
                    "b_fid": b_fid,
                    "old_code": None,
                    "old_name": None,
                    "predecessor": None,
                    "cluster_id": cluster_id,
                    "class": rel,
                    "match_method": None,
                }
                continue

            if rel in _SINGLE_PREDECESSOR_CLASSES:
                a_fid, b_fid = a_fids[0], b_fids[0]
                old_code = old_code_by_fid[a_fid]
                fid_key = f"n{n}_{b_fid}"
                new_batch.append((fid_key, new_parent_code(b_fid)))
                new_batch_meta[fid_key] = {
                    "b_fid": b_fid,
                    "old_code": old_code,
                    "old_name": old_name_by_fid.get(a_fid),
                    "predecessor": old_code,
                    "cluster_id": cluster_id,
                    "class": rel,
                    "match_method": pair_method.get((a_fid, b_fid)),
                }
                continue

            if rel == "split":
                a_fid = a_fids[0]
                old_code = old_code_by_fid[a_fid]
                for b_fid in b_fids:
                    fid_key = f"n{n}_{b_fid}"
                    new_batch.append((fid_key, new_parent_code(b_fid)))
                    new_batch_meta[fid_key] = {
                        "b_fid": b_fid,
                        "old_code": None,
                        "old_name": None,
                        "predecessor": old_code,
                        "cluster_id": cluster_id,
                        "class": rel,
                        "match_method": pair_method.get((a_fid, b_fid)),
                    }
                continue

            msg = f"unexpected relationship_class {rel!r}"
            raise ValueError(msg)

        if new_batch:
            staging = f"{name}_assign_{n}_new"
            conn.execute(f"""--sql
                CREATE OR REPLACE TEMP TABLE "{staging}" (
                    fid_key VARCHAR, code_val VARCHAR, parent_code VARCHAR
                )
            """)
            conn.executemany(
                f'INSERT INTO "{staging}" VALUES (?, ?, ?)',
                [(k, k, p) for k, p in new_batch],
            )
            assign_new_codes(
                conn,
                staging,
                id_column="fid_key",
                parent_column="parent_code",
                sort_columns=["fid_key"],
                code_column="code_val",
                fmt=fmt,
                existing_codes=retained_codes,
            )
            assigned = dict(
                conn.execute(f'SELECT fid_key, code_val FROM "{staging}"').fetchall()
            )
            conn.execute(f'DROP TABLE IF EXISTS "{staging}"')

            for fid_key, new_code in assigned.items():
                meta = new_batch_meta[fid_key]
                level_new_codes[meta["b_fid"]] = new_code
                changelog.append(
                    ChangeRow(
                        level=n,
                        old_code=meta["old_code"],
                        old_name=meta["old_name"],
                        new_code=new_code,
                        new_name=new_name_by_fid.get(meta["b_fid"]),
                        relationship_class=meta["class"],
                        cluster_id=meta["cluster_id"],
                        match_method=meta["match_method"],
                        code_outcome="new",
                        reason=_REASONS[(meta["class"], "new")],
                        predecessor_code=meta["predecessor"],
                        b_fid=meta["b_fid"],
                    )
                )

        new_code_by_fid[n] = level_new_codes

    return new_code_by_fid, changelog
