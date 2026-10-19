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
