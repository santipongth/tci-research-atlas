"""Thai text helpers shared by the parser, ingest, c-TF-IDF and search.

Thai code points are written with \\N{...} names on purpose: readable, and immune to
tools that decode backslash-u escapes.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

MARKS = "\N{THAI CHARACTER MAITAIKHU}-\N{THAI CHARACTER YAMAKKAN}"               # U+0E47–U+0E4E
ABOVE_BELOW = "\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER SARA I}-\N{THAI CHARACTER PHINTHU}"
THAI_LETTER = re.compile("[\N{THAI CHARACTER KO KAI}-\N{THAI CHARACTER HO NOKHUK}]")
LATIN_LETTER = re.compile(r"[A-Za-z]")
THAI_MARKS = re.compile(f"[{MARKS}]")
NIKHAHIT_SARA_AA = "\N{THAI CHARACTER NIKHAHIT}\N{THAI CHARACTER SARA AA}"
SARA_AM = "\N{THAI CHARACTER SARA AM}"

# Thai glyph variants in the Private Use Area left behind by PDF text extraction
# (legacy Thai font layout) → standard code points
THAI_PUA = {
    0xF700: 0x0E10, 0xF701: 0x0E34, 0xF702: 0x0E35, 0xF703: 0x0E36, 0xF704: 0x0E37,
    0xF705: 0x0E48, 0xF706: 0x0E49, 0xF707: 0x0E4A, 0xF708: 0x0E4B, 0xF709: 0x0E4C,
    0xF70A: 0x0E48, 0xF70B: 0x0E49, 0xF70C: 0x0E4A, 0xF70D: 0x0E4B, 0xF70E: 0x0E4C,
    0xF70F: 0x0E0D, 0xF710: 0x0E31, 0xF711: 0x0E4D, 0xF712: 0x0E47, 0xF713: 0x0E48,
    0xF714: 0x0E49, 0xF715: 0x0E4A, 0xF716: 0x0E4B, 0xF717: 0x0E4C, 0xF718: 0x0E38,
    0xF719: 0x0E39, 0xF71A: 0x0E3A,
}
_PUA_TABLE = str.maketrans(THAI_PUA)
_PUA_CHARS = re.compile("[" + "".join(map(chr, THAI_PUA)) + "]")
_SPACE_BEFORE_MARK = re.compile(f"\\s+([{ABOVE_BELOW}{MARKS}])")
_KEY_DROP = re.compile("[^0-9a-z\N{THAI CHARACTER KO KAI}-\N{THAI DIGIT NINE}]+")
_HAS_WORD_CHAR = re.compile("[0-9a-z\N{THAI CHARACTER KO KAI}-\N{THAI CHARACTER HO NOKHUK}]")
EN_STOPWORDS = frozenset(
    "a an and are as at be by for from has have in into is it its of on or that the this to was were "
    "with which we our their study research results using based among between".split()
)


def has_pua(s: str) -> bool:
    return bool(_PUA_CHARS.search(s or ""))


def repair_glyphs(s: str | None) -> str:
    """PUA + split sara-am repair only. Keeps whitespace runs (they separate abstract segments)."""
    if not s:
        return ""
    return unicodedata.normalize("NFC", s.translate(_PUA_TABLE)).replace(NIKHAHIT_SARA_AA, SARA_AM)


def clean_text(s: str | None) -> str:
    s = repair_glyphs(s)
    if not s:
        return ""
    s = _SPACE_BEFORE_MARK.sub(r"\1", s)          # "เจ้าหน้าท ี่" → "เจ้าหน้าที่"
    s = re.sub(r"</?[A-Za-z][^<>]*>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def fold_thai(s: str) -> str:
    """Remove Thai tone marks/diacritics — for matching text whose marks were lost."""
    return THAI_MARKS.sub("", s)


def thai_ratio(s: str) -> float:
    th, la = len(THAI_LETTER.findall(s)), len(LATIN_LETTER.findall(s))
    return th / (th + la) if th + la else 0.0


def norm_key(s: str) -> str:
    return _KEY_DROP.sub("", fold_thai(s.lower()))


@lru_cache(maxsize=1)
def _thai_stopwords() -> frozenset[str]:
    from pythainlp.corpus import thai_stopwords

    return frozenset(thai_stopwords())


def tokenize(text: str) -> list[str]:
    """Words for c-TF-IDF and search: Thai via pythainlp newmm, Latin lowercased."""
    from pythainlp.tokenize import word_tokenize

    stop = _thai_stopwords()
    out: list[str] = []
    for tok in word_tokenize(clean_text(text), engine="newmm", keep_whitespace=False):
        tok = tok.strip().lower().strip(".,;:()[]{}\"'“”‘’!?-–—/")
        if len(tok) < 2 or not _HAS_WORD_CHAR.search(tok) or tok.isdigit():
            continue
        if tok in stop or tok in EN_STOPWORDS:
            continue
        out.append(tok)
    return out
