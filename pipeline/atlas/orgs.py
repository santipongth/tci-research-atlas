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
    r"((?:[A-Z][\w'&.\-]*\s+){0,3}(?:University|Institute|College|Hospital|Polytechnic)"
    r"(?:\s+of(?:\s+[A-Z][\w'&.\-]*){1,4})?)"
)

# Contact details and street addresses are never part of an organisation name (PDPA): they are cut out before a
# name can be published.
_CONTACT = re.compile(
    r"(?:e-?mail|อีเมล|อีเมลล์|โทร\.?|tel\.?|fax)\s*[:：]?\s*"          # the label in front of an address / number
    r"|\S+@\S+"                                                      # e-mail address
    r"|https?://\S+|www\.\S+"                                          # web address
    r"|\+?\d[\d\s().\-]{6,}\d"                                        # phone number or a run of digits
    r"|\b\d{5}\b"                                                    # postcode
    r"|\d+/\d+"                                                       # house number 99/1
    r"|(?:หมู่(?:ที่)?|ม\.|ต\.|อ\.|ซ\.|ซอย|ถ\.|ถนน|แขวง|เขต|Moo|Soi|Road|Rd\.?)\s*\d+",  # village / lane / road numbers
    re.I)
# A name is published only when it names an organisation: it holds an organisation word. A bare "Somchai Jaidee"
# or "independent researcher, Bangkok" is counted (the totals stay right) but never listed or linked.
_ORG_WORDS = re.compile(
    r"มหาวิทยาลัย|สถาบัน|วิทยาลัย|โรงพยาบาล|โรงเรียน|กระทรวง|กรม|สำนักงาน|สำนัก|องค์การ|องค์กร|ศูนย์|บริษัท|ห้างหุ้นส่วน"
    r"|เทศบาล|สภา|สมาคม|มูลนิธิ|สหกรณ์|ราชวิทยาลัย|การไฟฟ้า|การประปา|ธนาคาร|พิพิธภัณฑ์|สถานี|คลินิก|ห้องปฏิบัติการ|หอสมุด"
    r"|Univ|Institute|College|Hospital|Polytechnic|Ministry|Department|Dept\b|Office|Cent(?:er|re)|Company|Co\.|Ltd"
    r"|School|Academy|Council|Foundation|Agency|Authority|Association|Society|Bureau|Bank|Corporation|Inc\b|Clinic"
    r"|Museum|Library|Laborator|Commission|Board|Observatory|Network|Faculty|Division|Group",
    re.I)
MAX_NAME_CHARS = 120
MAX_NAME_WORDS = 14


def strip_contact(text: str) -> str:
    """The text without e-mail / web / phone / postcode / house-number / village-and-road fragments."""
    return re.sub(r"\s{2,}", " ", _CONTACT.sub(" ", text or "")).strip(" ,;:-")


def is_org_name(name: str) -> bool:
    """True when `name` can be published as an institution name: short, free of contact details, and it holds
    an organisation word (so it cannot be only a person's name or a postal address)."""
    n = (name or "").strip()
    return bool(n) and len(n) <= MAX_NAME_CHARS and len(n.split()) <= MAX_NAME_WORDS and "@" not in n \
        and not _CONTACT.search(n) and bool(_ORG_WORDS.search(n))


_TH_NETWORKS = ("ราชภัฏ", "ราชมงคล", "บรมราชชนนี", "สิรินธร")      # one name for many separate institutions


def _th_org_token(th: str, word: str) -> str | None:
    """The first token holding `word`; a bare network name ("มหาวิทยาลัยราชภัฏ เชียงใหม่") takes the next token too."""
    m = re.search(rf"\S*{word}\S*(?:\s+(\S+))?", th)
    if not m:
        return None
    token = m.group(0).split()[0]
    if any(token.endswith(n) for n in _TH_NETWORKS) and m.group(1):
        return f"{token} {m.group(1)}"
    return token


def org_key(affiliation_th: str, affiliation_en: str) -> str:
    th = clean_text(affiliation_th)
    if th:
        for word in _TH_LEVELS:                 # most general organisation level first
            token = _th_org_token(th, word)
            if token:
                return norm_key(token)
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
    th = strip_contact(clean_text(affiliation_th))
    if th:
        for word in _TH_LEVELS:
            token = _th_org_token(th, word)
            if token:
                return token
        return th
    en = strip_contact(clean_text(affiliation_en))
    if en:
        m = _EN_ORG.search(en)
        return m.group(1).strip() if m else en
    return ""


def publishable_name(name: str) -> str:
    """`name` when it may be published as an institution name, else "" (see is_org_name)."""
    return name if is_org_name(name) else ""


def org_display_names(authors: pd.DataFrame) -> dict[str, str]:
    """{org_key: display name} — the most frequent publishable org_name among the author rows of each key (ties: the
    alphabetically first); a key with no publishable written form has no entry (it is counted, never named). One
    pass: names are computed per distinct affiliation pair, then one groupby."""
    if not {"org_key", "affiliation_th", "affiliation_en"} <= set(authors.columns):
        return {}
    a = pd.DataFrame({"org_key": authors["org_key"].fillna("").astype(str),
                      "th": authors["affiliation_th"].fillna("").astype(str),
                      "en": authors["affiliation_en"].fillna("").astype(str)})
    a = a[a["org_key"] != ""]
    pairs = a[["th", "en"]].drop_duplicates()
    pairs = pairs.assign(name=[publishable_name(org_name(t, e)) for t, e in zip(pairs["th"], pairs["en"])])
    named = a.merge(pairs, on=["th", "en"], how="left")
    named = named[named["name"] != ""]
    counts = named.groupby(["org_key", "name"]).size().rename("n").reset_index()
    best = counts.sort_values(["org_key", "n", "name"], ascending=[True, False, True]).drop_duplicates("org_key")
    return dict(zip(best["org_key"], best["name"]))
