"""Unit tests for schema_map's structural level/column detection."""

import duckdb
import pytest

from topo_tools.core.schema_map._level_columns import (
    detect_level_columns,
    group_families_by_level,
    is_level_identity_column,
    verify_functional_cluster,
)


@pytest.mark.parametrize(
    ("name", "prefix", "anchor", "suffix", "expected"),
    [
        ("adm3_pcode", "adm", "3", "_pcode", True),
        ("adm3_name2", "adm", "3", "_pcode", True),
        ("adm4_pcode", "adm", "3", "_pcode", False),
        ("area_sqkm", "adm", "3", "_pcode", False),
        ("state_name", "", "state", "_code", True),
        ("code_state", "code_", "state", "", True),
        ("code_county", "code_", "state", "", False),
    ],
)
def test_is_level_identity_column(name, prefix, anchor, suffix, expected):
    assert is_level_identity_column(name, prefix, anchor, suffix) is expected


@pytest.fixture
def conn():
    with duckdb.connect() as connection:
        connection.execute("INSTALL spatial; LOAD spatial;")
        yield connection


def _load_two_level_table(conn) -> None:
    conn.execute("""--sql
        CREATE TABLE t_01 AS
        SELECT row_number() OVER () AS fid, *
        FROM (VALUES
            ('P1', 'A1', 'Province1', 'Alpha',
             ST_GeomFromText('POLYGON((0 0,1 0,1 1,0 1,0 0))')),
            ('P1', 'A2', 'Province1', 'Beta',
             ST_GeomFromText('POLYGON((1 0,2 0,2 1,1 1,1 0))')),
            ('P2', 'B1', 'Province2', 'Gamma',
             ST_GeomFromText('POLYGON((0 1,1 1,1 2,0 2,0 1))'))
        ) AS v(adm1_pcode, adm2_pcode, adm1_name, adm2_name, geom)
    """)


def test_detect_level_columns_finds_coarser_and_finer_level(conn):
    _load_two_level_table(conn)
    result = detect_level_columns(conn, "t_01")
    coarser_level, finer_level = sorted(result)
    assert set(result[coarser_level].group_by) == {"adm1_pcode", "adm1_name"}
    assert set(result[finer_level].group_by) == {"adm2_pcode", "adm2_name"}
    assert set(result[coarser_level].identity_columns) == {"adm1_pcode", "adm1_name"}
    assert set(result[finer_level].identity_columns) == {"adm2_pcode", "adm2_name"}


def test_detect_level_columns_excludes_bijective_lookalike_from_identity(conn):
    conn.execute("""--sql
        CREATE TABLE t_01 AS
        SELECT row_number() OVER () AS fid, *
        FROM (VALUES
            ('P1', 'A1', 1.5, ST_GeomFromText('POLYGON((0 0,1 0,1 1,0 1,0 0))')),
            ('P1', 'A2', 2.5, ST_GeomFromText('POLYGON((1 0,2 0,2 1,1 1,1 0))')),
            ('P2', 'B1', 3.5, ST_GeomFromText('POLYGON((0 1,1 1,1 2,0 2,0 1))'))
        ) AS v(adm1_pcode, adm2_pcode, area_sqkm, geom)
    """)
    result = detect_level_columns(conn, "t_01")
    finer_level = max(result)
    assert "area_sqkm" not in result[finer_level].identity_columns


def test_detect_level_columns_ignores_floating_point_embed_coincidence(conn):
    """A low-cardinality flag must not masquerade as a level via a float's digits."""
    conn.execute("""--sql
        CREATE TABLE t_01 AS
        SELECT row_number() OVER () AS fid, *
        FROM (VALUES
            ('C0', 'C0A', 'Alpha', 1, 100.0,
             ST_GeomFromText('POLYGON((0 0,1 0,1 1,0 1,0 0))')),
            ('C0', 'C0B', 'Beta', 1, 210.0,
             ST_GeomFromText('POLYGON((1 0,2 0,2 1,1 1,1 0))')),
            ('C0', 'C0C', 'Gamma', 1, 310.0,
             ST_GeomFromText('POLYGON((0 1,1 1,1 2,0 2,0 1))')),
            ('C0', 'C0D', 'Delta', 2, 420.0,
             ST_GeomFromText('POLYGON((1 1,2 1,2 2,1 2,1 1))'))
        ) AS v(adm0_pcode, adm1_pcode, adm1_name, multipart, area_sqkm, geom)
    """)
    result = detect_level_columns(conn, "t_01")
    assert len(result) == 1
    (level,) = result
    assert set(result[level].group_by) == {"adm1_pcode", "adm1_name", "area_sqkm"}


def test_detect_level_columns_finds_flat_non_embedding_finest_level(conn):
    """A flat, non-compound finest-level code is still detected, via containment."""
    adm2_children = {
        "C0A1": ["5001", "5002", "5003"],
        "C0A2": ["5004", "5005", "5006"],
        "C0B1": ["5007", "5008", "5009"],
        "C0B2": ["5010", "5011", "5012"],
    }
    adm1_of = {"C0A1": "C0A", "C0A2": "C0A", "C0B1": "C0B", "C0B2": "C0B"}
    rows = []
    i = 0
    for adm2, children in adm2_children.items():
        for adm3 in children:
            square = f"POLYGON(({i} 0,{i + 1} 0,{i + 1} 1,{i} 1,{i} 0))"
            rows.append((adm1_of[adm2], adm2, adm3, square))
            i += 1
    values = ", ".join(
        f"('{a1}', '{a2}', '{a3}', ST_GeomFromText('{g}'))" for a1, a2, a3, g in rows
    )
    conn.execute(f"""--sql
        CREATE TABLE t_01 AS
        SELECT row_number() OVER () AS fid, 'C0' AS adm0_pcode, *
        FROM (VALUES {values}) AS v(adm1_pcode, adm2_pcode, adm3_pcode, geom)
    """)
    result = detect_level_columns(conn, "t_01")
    finest_level = max(result)
    assert result[finest_level].group_by == ["adm3_pcode"]


def test_detect_level_columns_ignores_coincidentally_embedding_sparse_columns(conn):
    """Sparse, single-row audit columns must not out-chain the real hierarchy."""
    adm2_children = {
        "C0A1": ["5001", "5002", "5003"],
        "C0A2": ["5004", "5005", "5006"],
        "C0B1": ["5007", "5008", "5009"],
        "C0B2": ["5010", "5011", "5012"],
    }
    adm1_of = {"C0A1": "C0A", "C0A2": "C0A", "C0B1": "C0B", "C0B2": "C0B"}
    rows = []
    i = 0
    for adm2, children in adm2_children.items():
        for adm3 in children:
            square = f"POLYGON(({i} 0,{i + 1} 0,{i + 1} 1,{i} 1,{i} 0))"
            audit = "' '" if i == 0 else "NULL"
            rows.append((adm1_of[adm2], adm2, adm3, audit, square))
            i += 1
    values = ", ".join(
        f"('{a1}', '{a2}', '{a3}', {audit}, ST_GeomFromText('{g}'))"
        for a1, a2, a3, audit, g in rows
    )
    conn.execute(f"""--sql
        CREATE TABLE t_01 AS
        SELECT row_number() OVER () AS fid, 'C0' AS adm0_pcode, *
        FROM (VALUES {values})
            AS v(adm1_pcode, adm2_pcode, adm3_pcode, comments, geom)
    """)
    conn.execute("""--sql
        ALTER TABLE t_01 ADD COLUMN focus_id VARCHAR;
        ALTER TABLE t_01 ADD COLUMN mod_by VARCHAR;
        ALTER TABLE t_01 ADD COLUMN progres_id VARCHAR;
        UPDATE t_01 SET focus_id = comments, mod_by = comments, progres_id = comments;
    """)
    result = detect_level_columns(conn, "t_01")
    assert any("adm1_pcode" in lc.group_by for lc in result.values())
    finest_level = max(result)
    assert result[finest_level].group_by == ["adm3_pcode"]


_LAST_ROW = 11


def test_detect_level_columns_ignores_low_cardinality_date_chains(conn):
    """A fully-populated pair of date audit columns must not out-chain a real level."""
    adm1_children = {
        "C0A": ["5001", "5002", "5003", "5004", "5005", "5006"],
        "C0B": ["5007", "5008", "5009", "5010", "5011", "5012"],
    }
    rows = []
    i = 0
    for adm1, children in adm1_children.items():
        for finest in children:
            square = f"POLYGON(({i} 0,{i + 1} 0,{i + 1} 1,{i} 1,{i} 0))"
            created = "2023-04-15" if i % 2 == 0 else "2023-06-01"
            # The last row was later re-edited, breaking the otherwise-clean
            # created_date/update_date bijection into a genuine embeds edge.
            updated = "2023-07-01" if i == _LAST_ROW else created
            rows.append((adm1, f"{adm1}{finest}", created, updated, square))
            i += 1
    values = ", ".join(
        f"('{a1}', '{f}', DATE '{c}', DATE '{d}', ST_GeomFromText('{g}'))"
        for a1, f, c, d, g in rows
    )
    conn.execute(f"""--sql
        CREATE TABLE t_01 AS
        SELECT row_number() OVER () AS fid, 'C0' AS adm0_pcode, *
        FROM (VALUES {values})
            AS v(adm1_pcode, finest_pcode, created_date, update_date, geom)
    """)
    result = detect_level_columns(conn, "t_01")
    assert any(lc.group_by == ["adm1_pcode"] for lc in result.values())
    finest_level = max(result)
    assert "finest_pcode" in result[finest_level].group_by


def test_detect_level_columns_word_based_anchor_both_positions(conn):
    conn.execute("""--sql
        CREATE TABLE t_01 AS
        SELECT row_number() OVER () AS fid, *
        FROM (VALUES
            ('P1', 'A1', NULL, NULL,
             ST_GeomFromText('POLYGON((0 0,1 0,1 1,0 1,0 0))')),
            ('P1', 'A2', NULL, NULL,
             ST_GeomFromText('POLYGON((1 0,2 0,2 1,1 1,1 0))')),
            ('P2', 'B1', NULL, NULL,
             ST_GeomFromText('POLYGON((0 1,1 1,1 2,0 2,0 1))'))
        ) AS v(state_code, county_code, state_name_alt, county_name_alt, geom)
    """)
    result = detect_level_columns(conn, "t_01")
    state_level, county_level = sorted(result)
    assert "state_name_alt" in result[state_level].identity_columns
    assert "county_name_alt" in result[county_level].identity_columns


def test_detect_level_columns_raises_when_no_level_found(conn):
    conn.execute("""--sql
        CREATE TABLE t_01 AS
        SELECT row_number() OVER () AS fid,
               ST_GeomFromText('POLYGON((0 0,1 0,1 1,0 1,0 0))') AS geom
    """)
    with pytest.raises(ValueError, match="no admin hierarchy level detected"):
        detect_level_columns(conn, "t_01")


def test_verify_functional_cluster_raises_on_fragmenting_member(conn):
    conn.execute("""--sql
        CREATE TABLE t_01 AS
        SELECT * FROM (VALUES
            ('P1', 'x'), ('P1', 'y'), ('P2', 'z')
        ) AS v(code, extra)
    """)
    with pytest.raises(ValueError, match="grouping by"):
        verify_functional_cluster(conn, "t_01", "code", ["code", "extra"])


def test_verify_functional_cluster_passes_on_matching_cardinality(conn):
    conn.execute("""--sql
        CREATE TABLE t_01 AS
        SELECT * FROM (VALUES
            ('P1', 'x'), ('P1', 'x'), ('P2', 'y')
        ) AS v(code, extra)
    """)
    verify_functional_cluster(conn, "t_01", "code", ["code", "extra"])


def test_group_families_by_level_word_based_anchor(conn):
    conn.execute("""--sql
        CREATE TABLE t_01 AS
        SELECT row_number() OVER () AS fid, *
        FROM (VALUES
            ('P1', 'A1', 'Province1', 'Alpha'),
            ('P1', 'A2', 'Province1', 'Beta'),
            ('P2', 'B1', 'Province2', 'Gamma')
        ) AS v(state_code, county_code, state_name, county_name)
    """)
    level_columns = detect_level_columns(conn, "t_01")
    families = group_families_by_level(conn, "t_01", level_columns)
    code_family = next(f for f in families.values() if set(f.values()) & {"state_code"})
    assert set(code_family.values()) == {"state_code", "county_code"}
