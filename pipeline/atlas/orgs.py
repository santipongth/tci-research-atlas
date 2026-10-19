"""Coarse institution key from an affiliation string, and the institution's display name.

org_key is good enough to COUNT distinct institutions (Emerging v2 breadth rule): it folds tone
marks and case so spelling variants collapse. It is never shown — the published name of an org_key
is its most frequent written form (org_display_names). P3 replaces both with the curated alias
table + ROR matching.
"""
from __future__ import annotations

import re

import pandas as pd

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


def org_name(affiliation_th: str, affiliation_en: str) -> str:
    """The organisation part of an affiliation as written — the text org_key is built from, cleaned (glyphs
    repaired, spaces normalised) but not folded: tone marks, karan and case stay. "คณะบริหารธุรกิจ
    มหาวิทยาลัยเกษตรศาสตร์" → "มหาวิทยาลัยเกษตรศาสตร์" (faculties and job titles are not published)."""
    th = clean_text(affiliation_th)
    if th:
        for word in _TH_LEVELS:
            m = re.search(rf"\S*{word}\S*", th)
            if m:
                return m.group(0)
        return th
    en = clean_text(affiliation_en)
    if en:
        m = _EN_ORG.search(en)
        return m.group(1).strip() if m else en
    return ""


def org_display_names(authors: pd.DataFrame) -> dict[str, str]:
    """{org_key: display name} — the most frequent org_name among the author rows of each key (ties: the
    alphabetically first). One pass: names are computed per distinct affiliation pair, then one groupby."""
    if not {"org_key", "affiliation_th", "affiliation_en"} <= set(authors.columns):
        return {}
    a = pd.DataFrame({"org_key": authors["org_key"].fillna("").astype(str),
                      "th": authors["affiliation_th"].fillna("").astype(str),
                      "en": authors["affiliation_en"].fillna("").astype(str)})
    a = a[a["org_key"] != ""]
    pairs = a[["th", "en"]].drop_duplicates()
    pairs = pairs.assign(name=[org_name(t, e) for t, e in zip(pairs["th"], pairs["en"])])
    named = a.merge(pairs, on=["th", "en"], how="left")
    named = named[named["name"] != ""]
    counts = named.groupby(["org_key", "name"]).size().rename("n").reset_index()
    best = counts.sort_values(["org_key", "n", "name"], ascending=[True, False, True]).drop_duplicates("org_key")
    return dict(zip(best["org_key"], best["name"]))
