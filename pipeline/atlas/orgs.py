"""Coarse institution key from an affiliation string.

Good enough to COUNT distinct institutions (Emerging v2 breadth rule). P3 replaces it
with the curated alias table + ROR matching.
"""
from __future__ import annotations

import re

from atlas.thai import clean_text, norm_key

_TH_LEVELS = ("มหาวิทยาลัย", "สถาบัน", "วิทยาลัย", "โรงพยาบาล")
_EN_ORG = re.compile(
    r"((?:[A-Z][\w'&.\-]*\s+){0,5}(?:University|Institute|College|Hospital|Polytechnic)"
    r"(?:\s+of(?:\s+[A-Z][\w'&.\-]*){1,4})?)"
)


def org_key(affiliation_th: str, affiliation_en: str) -> str:
    th = clean_text(affiliation_th)
    if th:
        for word in _TH_LEVELS:                 # most general organisation level first
            m = re.search(rf"\S*{word}\S*", th)
            if m:
                return norm_key(m.group(0))
        return norm_key(th)[:60]
    en = clean_text(affiliation_en)
    if en:
        m = _EN_ORG.search(en)
        return norm_key(m.group(1) if m else en)[:60]
    return ""
