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

# Contact details and street addresses are never part of an organisation name (PDPA): they are cut out before a
# key or a name is made. Labels only count when a number follows ("Tel Aviv", "Intel", "สถานีโทรทัศน์" stay whole);
# "เขต 1" / "เขต 9" are ordinals of districts and regions, not addresses, and stay too.
_CONTACT = re.compile(
    r"\b(?:e-?mail)\b\s*[:：]?|อีเมล(?:ล์)?\s*[:：]?"                    # an e-mail label (the address goes below)
    r"|\b(?:tel|fax|phone|mobile)\b\.?\s*[:：]?\s*(?=[+\d(])"             # a phone label followed by a number
    r"|โทร(?:ศัพท์|สาร)?\.?\s*[:：]?\s*(?=[+\d(])"
    r"|\S+@\S+"                                                         # e-mail address
    r"|https?://\S+|www\.\S+"                                          # web address
    r"|\+?\d[\d\s().\-]{6,}\d"                                         # phone number or a long run of digits
    r"|\b\d{5}\b"                                                      # postcode
    r"|\d+/\d+"                                                        # house number 99/1
    r"|(?:หมู่(?:ที่)?|\bMoo\b|\bSoi\b|ซอย|ซ\.)\s*\d+",                 # village / lane numbers
    re.I)
# A name is published only when it names an organisation: it holds an organisation word. A bare "Somchai Jaidee"
# or "independent researcher, Bangkok" is counted (the totals stay right) but never listed or linked.
_ORG_WORDS = re.compile(
    r"มหาวิทยาลัย|สถาบัน|วิทยาลัย|โรงพยาบาล|โรงเรียน|กระทรวง|กรม|กองทัพ|กอง|สำนักงาน|สำนัก|องค์การ|องค์กร|ศูนย์|บริษัท"
    r"|ห้างหุ้นส่วน|บมจ\.|บจก\.|หจก\.|เทศบาล|สภา|สมาคม|มูลนิธิ|สหกรณ์|ราชวิทยาลัย|การไฟฟ้า|การประปา|ธนาคาร|พิพิธภัณฑ์"
    r"|สถานี|คลินิก|ห้องปฏิบัติการ|หอสมุด|ตำรวจ|ศาล"
    r"|Univ|Institute|College|Hospital|Polytechnic|Ministry|Department|Dept\b|Office|Cent(?:er|re)|Company|Co\.|Ltd"
    r"|School|Academy|Council|Foundation|Agency|Authority|Association|Society|Bureau|Bank|Corporation|Inc\b|Clinic"
    r"|Museum|Library|Laborator|Commission|Board|Observatory|Network|Faculty|Division|Group|Organi[sz]ation|Army|Navy"
    r"|Air Force|Police|Court|Station|Unit\b|Programme|Program\b|Municipality",
    re.I)
MAX_NAME_CHARS = 120
MAX_NAME_WORDS = 14
# Tokens that can never be the campus after a network name: a person's title, a number, punctuation.
_NOT_A_PLACE = re.compile(r"^(?:นาย|นาง|นางสาว|ดร\.?|ผศ\.?|รศ\.?|ศ\.|อ\.|Mr|Mrs|Ms|Dr|Prof)|\d|^\W+$", re.I)


def strip_contact(text: str) -> str:
    """The text without e-mail / web / phone / postcode / house-number / village-and-lane fragments."""
    return re.sub(r"\s{2,}", " ", _CONTACT.sub(" ", text or "")).strip(" ,;:-")


def is_org_name(name: str) -> bool:
    """True when `name` can be published as an institution name: short, free of contact details, and it holds
    an organisation word (so it cannot be only a person's name or a postal address)."""
    n = (name or "").strip()
    return bool(n) and len(n) <= MAX_NAME_CHARS and len(n.split()) <= MAX_NAME_WORDS and "@" not in n \
        and not _CONTACT.search(n) and bool(_ORG_WORDS.search(n))


def has_org_word(text: str) -> bool:
    return bool(_ORG_WORDS.search(text or ""))


_TH_NETWORKS = ("ราชภัฏ", "ราชมงคล", "บรมราชชนนี", "สิรินธร")      # one name for many separate institutions


def _th_org_token(th: str) -> str | None:
    """The organisation token of a Thai affiliation. A network name ("มหาวิทยาลัยราชภัฏ", "…ราชมงคล",
    "วิทยาลัยพยาบาลบรมราชชนนี") wins over the level order and takes its campus — the next token, unless that is a
    person's title, a number or punctuation. Otherwise: the first token holding the most general level word."""
    tokens = th.split()
    for i, tok in enumerate(tokens):
        if any(w in tok for w in _TH_LEVELS) and any(tok.rstrip(",;.").endswith(n) for n in _TH_NETWORKS):
            tok = tok.rstrip(",;.")
            nxt = tokens[i + 1].strip(",;.") if i + 1 < len(tokens) else ""
            return f"{tok} {nxt}" if nxt and not _NOT_A_PLACE.search(nxt) else tok
    for word in _TH_LEVELS:                                     # most general organisation level first
        for i, tok in enumerate(tokens):
            if word in tok:
                tok = tok.strip(",;")
                nxt = tokens[i + 1].strip(",;.") if i + 1 < len(tokens) else ""
                # "โรงพยาบาลเขต 9": a district / region ordinal belongs to the name
                return f"{tok} {nxt}" if tok.endswith("เขต") and nxt.isdigit() else tok
    return None


def org_key(affiliation_th: str, affiliation_en: str) -> str:
    """Folded key of the organisation part — built from the same contact-free text as org_name, so one written
    name never splits into several keys by its phone number or address."""
    th = strip_contact(clean_text(affiliation_th))
    if th:
        token = _th_org_token(th)
        return norm_key(token) if token else norm_key(th)[:60]
    en = strip_contact(clean_text(affiliation_en))
    if en:
        m = _EN_ORG.search(en)
        return norm_key(m.group(1) if m else en)[:60]
    return ""


def org_name(affiliation_th: str, affiliation_en: str) -> str:
    """The organisation part of an affiliation as written — the text org_key is built from, cleaned (glyphs
    repaired, spaces normalised, contact details cut) but not folded: tone marks, karan and case stay.
    "คณะบริหารธุรกิจ มหาวิทยาลัยเกษตรศาสตร์" → "มหาวิทยาลัยเกษตรศาสตร์" (faculties and job titles are not published)."""
    th = strip_contact(clean_text(affiliation_th))
    if th:
        return _th_org_token(th) or th
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
