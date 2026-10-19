"""Is an affiliation outside Thailand? A small country lexicon (D3 "foreign authors") until P3 adds ROR.

Rule (precision first — a Thai institution must never count as foreign):
  * an affiliation that names Thailand ("Thailand", "ประเทศไทย") is Thai;
  * Thai text names a foreign country only with the word "ประเทศ" (or สปป.ลาว), because bare names such as
    "จีน" also name Thai departments ("ภาควิชาภาษาจีน");
  * English text names a foreign country as a whole word ("Japan", not "Japanese Studies" or "Thai-Japan Institute").
Only the share of articles with at least one such affiliation is published — never names.
"""
from __future__ import annotations

import re

from atlas.thai import clean_text

COUNTRIES_EN = (
    "Australia", "Austria", "Bangladesh", "Belgium", "Bhutan", "Brazil", "Brunei", "Cambodia", "Canada", "China",
    "Denmark", "Egypt", "England", "Finland", "France", "Germany", "Hong Kong", "India", "Indonesia", "Iran",
    "Italy", "Japan", "Kenya", "Korea", "Lao PDR", "Laos", "Macau", "Malaysia", "Mongolia", "Myanmar", "Nepal",
    "Netherlands", "New Zealand", "Nigeria", "Norway", "Pakistan", "Philippines", "Poland", "Russia",
    "Saudi Arabia", "Scotland", "Singapore", "South Africa", "Spain", "Sri Lanka", "Sweden", "Switzerland",
    "Taiwan", "Timor-Leste", "Turkey", "United Kingdom", "United States", "USA", "U.S.A.", "UK", "Viet Nam",
    "Vietnam",
)
COUNTRIES_TH = (
    "ญี่ปุ่น", "จีน", "เกาหลีใต้", "เกาหลี", "ลาว", "กัมพูชา", "เวียดนาม", "เมียนมา", "พม่า", "มาเลเซีย", "อินโดนีเซีย",
    "ฟิลิปปินส์", "สิงคโปร์", "บรูไน", "อินเดีย", "ภูฏาน", "เนปาล", "บังกลาเทศ", "ศรีลังกา", "ปากีสถาน", "ไต้หวัน",
    "ออสเตรเลีย", "นิวซีแลนด์", "สหรัฐอเมริกา", "อังกฤษ", "สหราชอาณาจักร", "เยอรมนี", "ฝรั่งเศส", "เนเธอร์แลนด์",
    "สวีเดน", "แคนาดา",
)
_EN = re.compile(r"(?<![\w.-])(?:" + "|".join(re.escape(c) for c in sorted(COUNTRIES_EN, key=len, reverse=True))
                 + r")(?![\w-])")
_TH = re.compile("ประเทศ\\s*(?:" + "|".join(sorted(COUNTRIES_TH, key=len, reverse=True)) + ")|สปป\\.?\\s*ลาว")
_THAILAND = re.compile(r"(?i)\bthailand\b|ประเทศไทย")


def is_foreign_affiliation(affiliation_th: str | None, affiliation_en: str | None) -> bool:
    th, en = clean_text(affiliation_th), clean_text(affiliation_en)
    if _THAILAND.search(th) or _THAILAND.search(en):
        return False
    return bool(_TH.search(th) or _EN.search(en))


# ISO 3166-1 alpha-2 of every name above (England, Scotland, UK → GB) and the names the web shows (th, en)
COUNTRY_ISO = {
    "Australia": "AU", "Austria": "AT", "Bangladesh": "BD", "Belgium": "BE", "Bhutan": "BT", "Brazil": "BR",
    "Brunei": "BN", "Cambodia": "KH", "Canada": "CA", "China": "CN", "Denmark": "DK", "Egypt": "EG", "England": "GB",
    "Finland": "FI", "France": "FR", "Germany": "DE", "Hong Kong": "HK", "India": "IN", "Indonesia": "ID", "Iran": "IR",
    "Italy": "IT", "Japan": "JP", "Kenya": "KE", "Korea": "KR", "Lao PDR": "LA", "Laos": "LA", "Macau": "MO",
    "Malaysia": "MY", "Mongolia": "MN", "Myanmar": "MM", "Nepal": "NP", "Netherlands": "NL", "New Zealand": "NZ",
    "Nigeria": "NG", "Norway": "NO", "Pakistan": "PK", "Philippines": "PH", "Poland": "PL", "Russia": "RU",
    "Saudi Arabia": "SA", "Scotland": "GB", "Singapore": "SG", "South Africa": "ZA", "Spain": "ES", "Sri Lanka": "LK",
    "Sweden": "SE", "Switzerland": "CH", "Taiwan": "TW", "Timor-Leste": "TL", "Turkey": "TR", "United Kingdom": "GB",
    "United States": "US", "USA": "US", "U.S.A.": "US", "UK": "GB", "Viet Nam": "VN", "Vietnam": "VN",
}
COUNTRY_ISO_TH = {
    "ญี่ปุ่น": "JP", "จีน": "CN", "เกาหลีใต้": "KR", "เกาหลี": "KR", "ลาว": "LA", "กัมพูชา": "KH", "เวียดนาม": "VN",
    "เมียนมา": "MM", "พม่า": "MM", "มาเลเซีย": "MY", "อินโดนีเซีย": "ID", "ฟิลิปปินส์": "PH", "สิงคโปร์": "SG", "บรูไน": "BN",
    "อินเดีย": "IN", "ภูฏาน": "BT", "เนปาล": "NP", "บังกลาเทศ": "BD", "ศรีลังกา": "LK", "ปากีสถาน": "PK", "ไต้หวัน": "TW",
    "ออสเตรเลีย": "AU", "นิวซีแลนด์": "NZ", "สหรัฐอเมริกา": "US", "อังกฤษ": "GB", "สหราชอาณาจักร": "GB", "เยอรมนี": "DE",
    "ฝรั่งเศส": "FR", "เนเธอร์แลนด์": "NL", "สวีเดน": "SE", "แคนาดา": "CA",
}
COUNTRY_NAMES: dict[str, tuple[str, str]] = {
    "TH": ("ไทย", "Thailand"), "AU": ("ออสเตรเลีย", "Australia"), "AT": ("ออสเตรีย", "Austria"),
    "BD": ("บังกลาเทศ", "Bangladesh"), "BE": ("เบลเยียม", "Belgium"), "BT": ("ภูฏาน", "Bhutan"), "BR": ("บราซิล", "Brazil"),
    "BN": ("บรูไน", "Brunei"), "KH": ("กัมพูชา", "Cambodia"), "CA": ("แคนาดา", "Canada"), "CN": ("จีน", "China"),
    "DK": ("เดนมาร์ก", "Denmark"), "EG": ("อียิปต์", "Egypt"), "GB": ("สหราชอาณาจักร", "United Kingdom"),
    "FI": ("ฟินแลนด์", "Finland"), "FR": ("ฝรั่งเศส", "France"), "DE": ("เยอรมนี", "Germany"), "HK": ("ฮ่องกง", "Hong Kong"),
    "IN": ("อินเดีย", "India"), "ID": ("อินโดนีเซีย", "Indonesia"), "IR": ("อิหร่าน", "Iran"), "IT": ("อิตาลี", "Italy"),
    "JP": ("ญี่ปุ่น", "Japan"), "KE": ("เคนยา", "Kenya"), "KR": ("เกาหลีใต้", "South Korea"), "LA": ("ลาว", "Laos"),
    "MO": ("มาเก๊า", "Macau"), "MY": ("มาเลเซีย", "Malaysia"), "MN": ("มองโกเลีย", "Mongolia"), "MM": ("เมียนมา", "Myanmar"),
    "NP": ("เนปาล", "Nepal"), "NL": ("เนเธอร์แลนด์", "Netherlands"), "NZ": ("นิวซีแลนด์", "New Zealand"),
    "NG": ("ไนจีเรีย", "Nigeria"), "NO": ("นอร์เวย์", "Norway"), "PK": ("ปากีสถาน", "Pakistan"),
    "PH": ("ฟิลิปปินส์", "Philippines"), "PL": ("โปแลนด์", "Poland"), "RU": ("รัสเซีย", "Russia"),
    "SA": ("ซาอุดีอาระเบีย", "Saudi Arabia"), "SG": ("สิงคโปร์", "Singapore"), "ZA": ("แอฟริกาใต้", "South Africa"),
    "ES": ("สเปน", "Spain"), "LK": ("ศรีลังกา", "Sri Lanka"), "SE": ("สวีเดน", "Sweden"),
    "CH": ("สวิตเซอร์แลนด์", "Switzerland"), "TW": ("ไต้หวัน", "Taiwan"), "TL": ("ติมอร์-เลสเต", "Timor-Leste"),
    "TR": ("ตุรกี", "Türkiye"), "US": ("สหรัฐอเมริกา", "United States"), "VN": ("เวียดนาม", "Vietnam"),
}


def country_of(affiliation_th: str | None, affiliation_en: str | None) -> str | None:
    """ISO alpha-2 of the country an affiliation names: "TH" when it names Thailand, a foreign code under the rules
    of is_foreign_affiliation, None when it names no country (most Thai affiliations)."""
    th, en = clean_text(affiliation_th), clean_text(affiliation_en)
    if _THAILAND.search(th) or _THAILAND.search(en):
        return "TH"
    if m := _TH.search(th):
        name = re.sub(r"^ประเทศ\s*", "", m.group(0))
        return "LA" if name.startswith("สปป") else COUNTRY_ISO_TH.get(name)
    m = _EN.search(en)
    return COUNTRY_ISO.get(m.group(0)) if m else None
