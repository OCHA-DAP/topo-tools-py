"""Annotate the hdx/topo-tools NLD collections after `portolan add`: titles, assets, extents and styles."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import duckdb
import yaml
from build_nld import ADMIN, YEARS, dataset_feed

LEVEL = {admin: level for level, admin in ADMIN.items()}
TOELICHTING = {
    2022: "https://www.cbs.nl/-/media/cbs/onze-diensten/methoden/onderzoek/pdf/2024/toelichting-wijk-en-buurtkaart-2022-2023-en-2024.pdf",
    **dict.fromkeys(
        (2023, 2024, 2025),
        "https://www.cbs.nl/-/media/cbs/onze-diensten/methoden/onderzoek/pdf/2025/toelichting-wijk-en-buurtkaart-2023-2024-en-2025.pdf",
    ),
}
LAND = {
    "nld_admin2": ("#3f8f5a", "#25583a"),
    "nld_admin3": ("#d18f2c", "#8a5a14"),
    "nld_admin4": ("#8a63b8", "#553a7a"),
}
WATER, BELGIUM = "#7fb3d5", "#b0b0b0"
COLUMNS = {
    "geometry": "Polygon or MultiPolygon in EPSG:28992 (RD New, metres). Gemeente boundaries come from Kadaster BRK and the land/water split from CBS Bestand Bodemgebruik. Not generalized.",
    "buurtcode": "Buurt (neighbourhood) code: `BU` plus 8 digits (4 gemeente, 2 wijk, 2 buurt). Water-only buurten end in `9997` (inland lakes) or `9998` (sea and estuaries).",
    "buurtnaam": "Buurt name, as set by the gemeente.",
    "wijkcode": "Wijk (district) code: `WK` plus 6 digits (4 gemeente, 2 wijk).",
    "wijknaam": "Wijk name, as set by the gemeente.",
    "gemeentecode": "Gemeente (municipality) code: `GM` plus 4 digits, set by CBS with the Ministry of the Interior (BZK). A rename changes the code.",
    "gemeentenaam": "Official gemeente name.",
    "water": "`JA` water, `NEE` land, `B` Belgian territory around Baarle-Nassau (gemeente `GM0998` Buitenland).",
    "jaar": "Vintage year of the Wijk- en Buurtkaart.",
    "bbox": "Per-row bounding box in EPSG:28992, for spatial filtering.",
}
DESCRIPTION = {
    "gemeenten": "{land} gemeenten from the CBS Wijk- en Buurtkaart {year}. {water} of them also have a water row sharing the gemeente code, and one `B` row (`GM0998` Buitenland) covers Belgian territory around Baarle-Nassau.",
    "wijken": "{land} wijken from the CBS Wijk- en Buurtkaart {year}, plus {water} water wijken and one `B` row for Belgian territory around Baarle-Nassau.",
    "buurten": "{land} buurten from the CBS Wijk- en Buurtkaart {year}, plus {water} water buurten (codes ending in `9997` or `9998`) and one `B` row for Belgian territory around Baarle-Nassau.",
}
DEMO = {
    "": {
        "title": "Netherlands demo inputs",
        "description": "Input layers for trying each topo-tools tool on Dutch boundaries. Each folder is named after the tool it's for and holds the files that tool takes, simplified to 100 m. Running a tool on its input produces the output, which is never stored here. See [AGENTS.md](AGENTS.md).",
    },
    "schema-map": {
        "title": "Gemeenten 2025",
        "description": "The 342 land gemeenten from the CBS Wijk- en Buurtkaart 2025, in EPSG:28992 with the CBS column names. Boundaries are simplified to 100 m, with neighbouring gemeenten still sharing their edges. The provincie code and name come from CBS StatLine table 86059NED (Gebieden in Nederland 2025). Running schema-map on it maps the gemeente columns to adm2 and the provincie columns to adm1. It drops `landcode`, `landnaam`, `water` and `jaar` because each holds a single value. See [AGENTS.md](AGENTS.md).",
        "keywords": [
            "administrative boundaries",
            "Netherlands",
            "CBS",
            "gemeenten",
            "provincies",
            "topo-tools",
            "schema-map",
        ],
        "processing_notes": "Built by `catalog/build_demo.py` in [topo-tools-py](https://github.com/OCHA-DAP/topo-tools-py) from the land rows of `nld/2025/nld_admin2`: `ST_CoverageSimplify` at 100 m, then `ST_CoverageClean` with 0.01 m snapping and no gap filling. Provincie columns joined on `gemeentecode` from the CBS StatLine [OData table 86059NED](https://opendata.cbs.nl/ODataApi/odata/86059NED/TypedDataSet?$format=json&$select=RegioS,Code_28,Naam_29).",
    },
    "schema-join": {
        "title": "Gemeenten and provincies 2025",
        "description": "An input and a join layer for schema-join, in EPSG:28992, simplified to 100 m. `nld_admin2.parquet` has the 342 land gemeenten from the CBS Wijk- en Buurtkaart 2025, with `adm2_code` and `adm2_name`. `nld_admin1.parquet` has the 12 provincies from Kadaster Bestuurlijke Gebieden, with `adm1_code` and `adm1_name`. Running schema-join copies each gemeente's provincie code and name onto it. See [AGENTS.md](AGENTS.md).",
        "keywords": [
            "administrative boundaries",
            "Netherlands",
            "CBS",
            "Kadaster",
            "gemeenten",
            "provincies",
            "topo-tools",
            "schema-join",
        ],
        "processing_notes": "Built by `catalog/build_demo.py` in [topo-tools-py](https://github.com/OCHA-DAP/topo-tools-py): gemeenten from the land rows of `nld/2025/nld_admin2`, and provincies from the PDOK [Bestuurlijke Gebieden OGC API](https://api.pdok.nl/kadaster/bestuurlijkegebieden/ogc/v1) (`provinciegebied`, retrieved 2026-09-28). Each layer is simplified with `ST_CoverageSimplify` at 100 m, then `ST_CoverageClean` with 0.01 m snapping and no gap filling.",
    },
}
for fields in DEMO.values():
    fields.setdefault(
        "keywords", ["administrative boundaries", "Netherlands", "CBS", "topo-tools"]
    )
DEMO_COLUMNS = {
    **COLUMNS,
    "geometry": "Polygon or MultiPolygon in EPSG:28992 (RD New, metres), simplified to 100 m with `ST_CoverageSimplify` so neighbouring gemeenten keep shared edges.",
    "provinciecode": "Provincie code: `PV` plus 2 digits, from CBS StatLine table 86059NED.",
    "provincienaam": "Provincie name, from CBS StatLine table 86059NED.",
    "landcode": "Country code, always `NL`.",
    "landnaam": "Country name, always `Nederland`.",
    "water": "Always `NEE` (land). Water rows are left out.",
}
JOIN_COLUMNS = {
    "geometry": "Polygon or MultiPolygon in EPSG:28992 (RD New, metres), simplified to 100 m with `ST_CoverageSimplify` so neighbours keep shared edges. Provincies include water; gemeenten are land only.",
    "adm2_code": "Gemeente code: `GM` plus 4 digits, from CBS.",
    "adm2_name": "Official gemeente name, from CBS.",
    "adm1_code": "Provincie code: `PV` plus 2 digits, from Kadaster (`identificatie`).",
    "adm1_name": "Provincie name, from Kadaster.",
    "bbox": COLUMNS["bbox"],
}
PROVINCIES = {
    "Groningen": "#a6cee3",
    "Fryslân": "#1f78b4",
    "Drenthe": "#b2df8a",
    "Overijssel": "#33a02c",
    "Flevoland": "#fb9a99",
    "Gelderland": "#e31a1c",
    "Utrecht": "#fdbf6f",
    "Noord-Holland": "#ff7f00",
    "Zuid-Holland": "#cab2d6",
    "Zeeland": "#6a3d9a",
    "Noord-Brabant": "#e6d93f",
    "Limburg": "#b15928",
}

DATA = "https://data.source.coop/hdx/topo-tools"
TEMPLATES = Path(__file__).parent / "agents"
REVISION = {2021: 3, 2022: 3, 2023: 3, 2024: 2, 2025: 1}
UNIT = {
    "gemeenten": ("gemeentecode", "gemeentenaam", ""),
    "wijken": ("wijkcode", "wijknaam", " The parent code is `gemeentecode`."),
    "buurten": (
        "buurtcode",
        "buurtnaam",
        " The parent codes are `wijkcode` and `gemeentecode`.",
    ),
}
LARGEST_GEMEENTEN = """-- Largest gemeenten by land area in km²
SELECT gemeentecode, gemeentenaam, round(sum(ST_Area(geometry)) / 1e6, 1) AS land_km2
FROM read_parquet('{url}')
WHERE water = 'NEE'
GROUP BY ALL ORDER BY land_km2 DESC LIMIT 3;
-- {top}"""
UNIT_AREA = """-- Land area per unit in km²
SELECT {code}, {name}, ST_Area(geometry) / 1e6 AS km2
FROM read_parquet('{url}')
WHERE water = 'NEE';"""


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000)
    )


def collection_metadata(parquet: Path, admin: str, year: int) -> dict:
    land, water = duckdb.execute(
        f"SELECT count(*) FILTER (WHERE water = 'NEE'), count(*) FILTER (WHERE water = 'JA') FROM read_parquet('{parquet}')"
    ).fetchone()
    level = LEVEL[admin]
    description = DESCRIPTION[level].format(land=land, water=water, year=year)
    return {
        "title": f"Netherlands {admin.removeprefix('nld_')} ({level}) {year}",
        "description": f"{description} Agents should start at [AGENTS.md](AGENTS.md).",
    }


def file_fields(path: Path) -> dict:
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    return {"file:size": path.stat().st_size, "file:checksum": f"1220{digest}"}


def cached_pdf(url: str, cache: Path) -> Path:
    path = cache / url.rsplit("/", 1)[1]
    if not path.exists():
        subprocess.run(
            ["curl", "-fsSL", "-A", "Mozilla/5.0", "-o", str(path), url], check=True
        )
    return path


def extra_assets(year: int, cache: Path) -> dict:
    feed = dataset_feed(year)
    gpkg = re.search(r'<link href="([^"]+\.gpkg)"', feed).group(1)
    iso = re.search(r'<link href="([^"]+GetRecordById[^"]+)"', feed).group(1)
    assets = {
        "source": {
            "href": gpkg,
            "type": "application/geopackage+sqlite3",
            "roles": ["source"],
            "title": f"Wijk- en Buurtkaart {year} GeoPackage, PDOK Atom download",
            **file_fields(cache / f"wijkenbuurten_{year}.gpkg"),
        },
        "iso-19115": {
            "href": iso.replace("&amp;", "&"),
            "type": "application/xml",
            "roles": ["metadata", "iso-19115"],
            "title": f"Wijk- en Buurtkaart {year} ISO 19115 record, Nationaal Georegister",
        },
    }
    if year in TOELICHTING:
        assets["toelichting"] = {
            "href": TOELICHTING[year],
            "type": "application/pdf",
            "roles": ["metadata"],
            "title": "CBS Toelichting Wijk- en Buurtkaart (column definitions)",
            **file_fields(cached_pdf(TOELICHTING[year], cache)),
        }
    return assets


def style(admin: str, source: dict) -> dict:
    land, outline = LAND[admin]
    return {
        "version": 8,
        "name": "Land and water",
        "sources": {"data": source},
        "layers": [
            {
                "id": f"{admin}-fill",
                "type": "fill",
                "source": "data",
                "source-layer": admin,
                "paint": {
                    "fill-color": [
                        "match",
                        ["get", "water"],
                        "NEE",
                        land,
                        "JA",
                        WATER,
                        "B",
                        BELGIUM,
                        "#cccccc",
                    ],
                    "fill-opacity": 0.7,
                },
            },
            {
                "id": f"{admin}-outline",
                "type": "line",
                "source": "data",
                "source-layer": admin,
                "paint": {"line-color": outline, "line-width": 0.5},
            },
        ],
    }


def annotate(collection_dir: Path, admin: str, year: int, assets: dict) -> None:
    path = collection_dir / "collection.json"
    collection = json.loads(path.read_text())
    for column in collection["table:columns"]:
        if column["name"] in COLUMNS:
            column["description"] = COLUMNS[column["name"]]
    reference = f"{year}-01-01T00:00:00Z"
    collection["extent"]["temporal"]["interval"] = [[reference, reference]]
    collection["assets"].update(assets)

    style_path = collection_dir / "styles" / "default.json"
    source = json.loads(style_path.read_text())["sources"]["data"]
    style_path.write_text(json.dumps(style(admin, source), indent=2) + "\n")
    for asset in collection["assets"].values():
        local = collection_dir / asset["href"]
        if "://" not in asset["href"] and local.exists():
            asset.update(file_fields(local))
    path.write_text(json.dumps(collection, indent=2, ensure_ascii=False) + "\n")


def template(name: str, **fields: str) -> str:
    return (TEMPLATES / f"{name}.md").read_text().format(data=DATA, **fields)


def collection_agents(parquet: Path, admin: str, year: int) -> str:
    level = LEVEL[admin]
    code, name, parents = UNIT[level]
    url = f"{DATA}/nld/{year}/{admin}/{admin}.parquet"
    con = duckdb.connect()
    con.execute("LOAD spatial")
    counts = dict(
        con.execute(
            f"SELECT water, count(*) FROM read_parquet('{parquet}') GROUP BY water ORDER BY water"
        ).fetchall()
    )
    if level == "gemeenten":
        rows = f"{counts['NEE']:,} land gemeenten, {counts['JA']} water rows sharing their gemeente's code and one `B` row"
        top = con.execute(
            f"SELECT gemeentecode, gemeentenaam, round(ST_Area(geometry) / 1e6, 1) FROM read_parquet('{parquet}') "
            "WHERE water = 'NEE' ORDER BY 3 DESC LIMIT 1"
        ).fetchone()
        area = LARGEST_GEMEENTEN.format(url=url, top=f"{top[0]} {top[1]}, {top[2]}")
    else:
        rows = f"{counts['NEE']:,} land {level}, {counts['JA']} water {level} and one `B` row"
        area = UNIT_AREA.format(code=code, name=name, url=url)
    return template(
        "collection",
        title=collection_metadata(parquet, admin, year)["title"],
        rows=rows,
        year=str(year),
        code=code,
        parents=parents,
        url=url,
        counts=", ".join(f"{k} {v}" for k, v in counts.items()),
        area=area,
    )


def write_agents(catalog: Path) -> None:
    (catalog / "AGENTS.md").write_text(template("root"))
    (catalog / "nld" / "AGENTS.md").write_text(template("nld"))
    for year in YEARS:
        year_dir = catalog / "nld" / str(year)
        (year_dir / "AGENTS.md").write_text(
            template("year", year=str(year), revision=str(REVISION[year]))
        )
        for admin in LEVEL:
            (year_dir / admin / "AGENTS.md").write_text(
                collection_agents(year_dir / admin / f"{admin}.parquet", admin, year)
            )


def demo_collection(collection_dir: Path, columns: dict) -> None:
    path = collection_dir / "collection.json"
    collection = json.loads(path.read_text())
    for column in collection["table:columns"]:
        if column["name"] in columns:
            column["description"] = columns[column["name"]]
    collection["extent"]["temporal"]["interval"] = [["2025-01-01T00:00:00Z"] * 2]
    for asset in collection["assets"].values():
        local = collection_dir / asset["href"]
        if "://" not in asset["href"] and local.exists():
            asset.update(file_fields(local))
    path.write_text(json.dumps(collection, indent=2, ensure_ascii=False) + "\n")


def provincie_style(collection_dir: Path) -> None:
    style_path = collection_dir / "styles" / "default.json"
    source = json.loads(style_path.read_text())["sources"]["data"]
    fill = ["match", ["get", "provincienaam"]]
    for name, color in PROVINCIES.items():
        fill += [name, color]
    provincie_style = {
        "version": 8,
        "name": "Provincies",
        "sources": {"data": source},
        "layers": [
            {
                "id": "nld_admin2-fill",
                "type": "fill",
                "source": "data",
                "source-layer": "nld_admin2",
                "paint": {"fill-color": [*fill, "#cccccc"], "fill-opacity": 0.7},
            },
            {
                "id": "nld_admin2-outline",
                "type": "line",
                "source": "data",
                "source-layer": "nld_admin2",
                "paint": {"line-color": "#333333", "line-width": 0.5},
            },
        ],
    }
    style_path.write_text(
        json.dumps(provincie_style, indent=2, ensure_ascii=False) + "\n"
    )


def annotate_schema_map(collection_dir: Path, cache: Path) -> None:
    provincie_style(collection_dir)
    demo_collection(collection_dir, DEMO_COLUMNS)
    url = f"{DATA}/nld/demo/schema-map/nld_admin2.parquet"
    parquet = collection_dir / "nld_admin2.parquet"
    counts = duckdb.execute(
        f"SELECT provinciecode, provincienaam, count(*) FROM read_parquet('{parquet}') GROUP BY ALL ORDER BY 1"
    ).fetchall()
    rows = sum(n for *_, n in counts)
    crosswalk = duckdb.execute(
        f"SELECT source_column, coalesce(target_column, 'dropped'), unique_count FROM read_csv('{cache / 'schema-map' / 'nld_admin2_crosswalk.csv'}', all_varchar=true)"
    ).fetchall()
    gaps = duckdb.execute(
        f"SELECT count(*) FROM read_parquet('{cache / 'schema-map_nld_admin2_issues.parquet'}') WHERE kind = 'gap'"
    ).fetchone()[0]
    (collection_dir / "AGENTS.md").write_text(
        template(
            "demo_schema_map",
            title=DEMO["schema-map"]["title"],
            rows=str(rows),
            url=url,
            crosswalk="\n".join(
                ["| source_column | target_column | unique_count |", "|---|---|---|"]
                + [
                    f"| `{c}` | {t if t == 'dropped' else f'`{t}`'} | {n} |"
                    for c, t, n in crosswalk
                ]
            ),
            gaps=str(gaps),
            counts=", ".join(f"{c} {name} {n}" for c, name, n in counts),
        )
    )


def join_style(collection_dir: Path) -> None:
    style_path = collection_dir / "styles" / "default.json"
    source = next(iter(json.loads(style_path.read_text())["sources"].values()))
    sources = {
        layer: {**source, "url": source["url"].replace("nld_admin1", layer)}
        for layer in ("nld_admin1", "nld_admin2")
    }
    fill = ["match", ["get", "adm1_name"]]
    for name, color in PROVINCIES.items():
        fill += [name, color]
    join_style = {
        "version": 8,
        "name": "Provincies and gemeenten",
        "sources": sources,
        "layers": [
            {
                "id": "nld_admin1-fill",
                "type": "fill",
                "source": "nld_admin1",
                "source-layer": "nld_admin1",
                "paint": {"fill-color": [*fill, "#cccccc"], "fill-opacity": 0.7},
            },
            {
                "id": "nld_admin2-outline",
                "type": "line",
                "source": "nld_admin2",
                "source-layer": "nld_admin2",
                "paint": {"line-color": "#333333", "line-width": 0.5},
            },
            {
                "id": "nld_admin1-outline",
                "type": "line",
                "source": "nld_admin1",
                "source-layer": "nld_admin1",
                "paint": {"line-color": "#000000", "line-width": 1.5},
            },
        ],
    }
    style_path.write_text(json.dumps(join_style, indent=2, ensure_ascii=False) + "\n")


def annotate_schema_join(collection_dir: Path) -> None:
    join_style(collection_dir)
    demo_collection(collection_dir, JOIN_COLUMNS)
    url = f"{DATA}/nld/demo/schema-join"
    con = duckdb.connect()
    con.execute("LOAD spatial")
    rows = con.execute(
        f"SELECT count(*) FROM read_parquet('{collection_dir / 'nld_admin2.parquet'}')"
    ).fetchone()[0]
    areas = con.execute(
        "SELECT adm1_code, adm1_name, round(ST_Area(geometry) / 1e6)::INT "
        f"FROM read_parquet('{collection_dir / 'nld_admin1.parquet'}') ORDER BY 1"
    ).fetchall()
    (collection_dir / "AGENTS.md").write_text(
        template(
            "demo_schema_join",
            title=DEMO["schema-join"]["title"],
            rows=str(rows),
            input=f"{url}/nld_admin2.parquet",
            join=f"{url}/nld_admin1.parquet",
            areas=", ".join(f"{c} {name} {km2}" for c, name, km2 in areas),
        )
    )


def apply_titles(catalog: Path) -> None:
    for metadata in catalog.rglob(".portolan/metadata.yaml"):
        fields = yaml.safe_load(metadata.read_text()) or {}
        for name in ("catalog.json", "collection.json"):
            stac_path = metadata.parent.parent / name
            if stac_path.exists() and {"title", "description"} <= fields.keys():
                stac = json.loads(stac_path.read_text())
                stac["title"], stac["description"] = (
                    fields["title"],
                    fields["description"],
                )
                stac_path.write_text(
                    json.dumps(stac, indent=2, ensure_ascii=False) + "\n"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog", type=Path, required=True, help="Catalog root directory"
    )
    parser.add_argument("--cache", type=Path, default=Path("tmp/catalog/cache"))
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Write metadata.yaml files only (run before `portolan add`)",
    )
    args = parser.parse_args()

    for year in YEARS:
        year_dir = args.catalog / "nld" / str(year)
        write_yaml(
            year_dir / ".portolan" / "metadata.yaml",
            {
                "title": str(year),
                "description": f"CBS Wijk- en Buurtkaart {year}: gemeenten (admin2), wijken (admin3) and buurten (admin4).",
            },
        )
        assets = None if args.metadata_only else extra_assets(year, args.cache)
        for admin in LEVEL:
            collection_dir = year_dir / admin
            write_yaml(
                collection_dir / ".portolan" / "metadata.yaml",
                collection_metadata(collection_dir / f"{admin}.parquet", admin, year),
            )
            if assets is not None:
                annotate(collection_dir, admin, year, assets)
    demo = args.catalog / "nld" / "demo"
    for path, fields in DEMO.items():
        if (demo / path).exists():
            write_yaml(demo / path / ".portolan" / "metadata.yaml", fields)
    if not args.metadata_only:
        apply_titles(args.catalog)
        write_agents(args.catalog)
        if demo.exists():
            (demo / "AGENTS.md").write_text(template("demo"))
            annotate_schema_map(demo / "schema-map", args.cache / "demo")
            annotate_schema_join(demo / "schema-join")


if __name__ == "__main__":
    main()
