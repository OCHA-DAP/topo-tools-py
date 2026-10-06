# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "tenacity",
#     "truststore",
# ]
# ///
"""Regenerate data/m49.csv from the UN M49 overview page, in all six UN languages.

uv run <skill-dir>/scripts/m49.py
"""

import csv
import logging
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

import truststore
from tenacity import retry, stop_after_attempt, wait_exponential

truststore.inject_into_ssl()
logging.basicConfig(format="%(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

_URL = "https://unstats.un.org/unsd/methodology/m49/overview/"
_OUT = Path(__file__).resolve().parent.parent / "data" / "m49.csv"
_TABS = {"ar": "ARB", "zh": "CHN", "en": "ENG", "fr": "FRA", "ru": "RUS", "es": "ESP"}
_NAME, _M49, _ISO2, _ISO3 = 8, 9, 10, 11


class _Tables(HTMLParser):
    """Collect each language tab's body rows, keyed by tab id."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: dict[str, list[list[str]]] = {}
        self._tab: str | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._in_body = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        tab = dict(attrs).get("id", "") or ""
        if tag == "div" and tab.endswith("_Overview"):
            self._tab = tab.removesuffix("_Overview")
            self.rows[self._tab] = []
        elif tag == "tbody":
            self._in_body = True
        elif tag == "tr" and self._in_body:
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._cell is not None and self._row is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None and self._tab:
            self.rows[self._tab].append(self._row)
            self._row = None
        elif tag == "tbody":
            self._in_body = False

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2), reraise=True)
def _fetch() -> str:
    request = urllib.request.Request(_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 (hardcoded https)
        return response.read().decode("utf-8")


def main() -> None:
    """Write every M49 area's codes and names, one column per UN language."""
    parser = _Tables()
    parser.feed(_fetch())
    names: dict[str, dict[str, str]] = {}
    codes: dict[str, tuple[str, str]] = {}
    for lang, tab in _TABS.items():
        for row in parser.rows.get(tab, []):
            names.setdefault(row[_M49], {})[lang] = row[_NAME]
            codes.setdefault(row[_M49], (row[_ISO2], row[_ISO3]))
    if not names or any(len(langs) != len(_TABS) for langs in names.values()):
        msg = "the six language tabs don't list the same M49 codes"
        raise SystemExit(msg)
    _OUT.parent.mkdir(exist_ok=True)
    with _OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["m49", "iso2", "iso3", *(f"name_{lang}" for lang in _TABS)])
        for m49 in sorted(names):
            writer.writerow([m49, *codes[m49], *(names[m49][lang] for lang in _TABS)])
    log.info("wrote %d rows to %s", len(names), _OUT)


if __name__ == "__main__":
    main()
