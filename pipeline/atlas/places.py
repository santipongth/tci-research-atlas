"""Thai provinces (77, ISO 3166-2:TH) and the province named in an affiliation.

atlas/data/th_provinces.csv is public reference data (codes, Thai and English names, other spellings). The region
follows the National Statistical Office's four regions + Bangkok and is decided by the code: 10 Bangkok · 11–27 and
70–77 central (incl. east and west) · 30–49 northeast · 50–67 north · 80–96 south.

province_finder().find(th, en) — precision first (a wrong province is worse than none):
  Thai     a province name right after จังหวัด / จ. / ราชภัฏ / มหาวิทยาลัย / โรงพยาบาล / วิทยาลัยพยาบาลบรมราชชนนี,
           or กรุงเทพ anywhere (text folded like org keys: tone marks, spaces and dots ignored)
  English  a province name as a whole word, spaces optional ("Chiang Mai", "Chiangmai"), or an alt_en spelling
  The first province named wins (an affiliation names its main location first). Thai text is read before English.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from atlas.thai import clean_text, norm_key

PROVINCES_CSV = Path(__file__).parent / "data" / "th_provinces.csv"
REGIONS = ("bangkok", "central", "northeast", "north", "south")
# Words that put a province name right after them. A bare "จ" is not one: folded, it is also the last letter of
# ธุรกิจ / เศรษฐกิจ / วิจัย… ("ศูนย์วิจัยเศรษฐกิจตาก" is not in Tak). "จ." / "จังหวัด" are read first, unfolded.
_TH_PREFIXES = ("จังหวัด", "ราชภัฏ", "มหาวิทยาลัย", "โรงพยาบาล", "วิทยาลัยพยาบาลบรมราชชนนี")
_MARKED = re.compile(r"(?:^|(?<=[\s,(]))(?:จังหวัด|จ\.)\s*(\S+)")


@dataclass(frozen=True)
class Province:
    code: str
    name_th: str
    name_en: str
    region: str


def region_of(code: str) -> str:
    n = int(code.split("-")[1])
    if n == 10:
        return "bangkok"
    if 11 <= n <= 27 or 70 <= n <= 77:
        return "central"
    if 30 <= n <= 49:
        return "northeast"
    if 50 <= n <= 67:
        return "north"
    return "south"


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    with PROVINCES_CSV.open(encoding="utf-8", newline="") as f:
        return tuple({k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f))


@lru_cache(maxsize=1)
def provinces() -> dict[str, Province]:
    return {r["code"]: Province(r["code"], r["name_th"], r["name_en"], region_of(r["code"])) for r in _rows()}


class ProvinceFinder:
    def __init__(self, rows):
        th_names: dict[str, str] = {}
        en_names: dict[str, str] = {}
        for r in rows:
            for n in [r["name_th"], *filter(None, r["alt_th"].split(";"))]:
                th_names[norm_key(n)] = r["code"]
            for n in [r["name_en"], *filter(None, r["alt_en"].split(";"))]:
                en_names[n.strip().lower()] = r["code"]
        self._th_code = th_names
        self._by_length = sorted(th_names, key=len, reverse=True)
        names = "|".join(re.escape(k) for k in sorted(th_names, key=len, reverse=True))
        prefixes = "|".join(re.escape(norm_key(p)) for p in _TH_PREFIXES)
        self._th = re.compile(f"(?:{prefixes})({names})")
        self._bangkok = norm_key("กรุงเทพ")
        self._en_code = {re.sub(r"\s", "", k): v for k, v in en_names.items()}
        words = [r"\s?".join(re.escape(w) for w in k.split()) for k in sorted(en_names, key=len, reverse=True)]
        self._en = re.compile(r"(?<![a-z])(" + "|".join(words) + r")(?![a-z])")

    def _marked(self, text: str) -> str | None:
        """The province named right after "จังหวัด" / "จ." — the last such mention (it is the address, at the end)."""
        found = None
        for m in _MARKED.finditer(text):
            word = norm_key(m.group(1))
            for name in self._by_length:
                if word.startswith(name):
                    found = self._th_code[name]
                    break
        return found

    def find(self, affiliation_th: str | None, affiliation_en: str | None) -> str | None:
        raw = clean_text(affiliation_th)
        if code := self._marked(raw):
            return code                              # an explicit "จังหวัด…" beats a name inside a university's name
        th = norm_key(raw)
        hits = []
        if m := self._th.search(th):
            hits.append((m.start(), self._th_code[m.group(1)]))
        if (b := th.find(self._bangkok)) >= 0:
            hits.append((b, "TH-10"))
        if hits:
            return min(hits)[1]
        m = self._en.search(clean_text(affiliation_en).lower())
        return self._en_code[re.sub(r"\s", "", m.group(1))] if m else None


@lru_cache(maxsize=1)
def province_finder() -> ProvinceFinder:
    return ProvinceFinder(_rows())
