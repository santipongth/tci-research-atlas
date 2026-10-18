import unicodedata

import pytest

from atlas.thai import THAI_PUA, clean_text, fold_thai, has_pua, norm_key, repair_glyphs, thai_ratio, tokenize

MAI_THO = "\N{THAI CHARACTER MAI THO}"
SARA_AM = "\N{THAI CHARACTER SARA AM}"


def test_clean_text_maps_pua_tone_marks_to_standard():
    broken = "ความต" + chr(0xF70B) + "องการ"  # PUA mai tho from PDF extraction
    assert clean_text(broken) == "ความต" + MAI_THO + "องการ"
    assert has_pua(broken) and not has_pua(clean_text(broken))


def test_clean_text_repairs_split_sara_am_and_space_before_mark():
    split = "ตำแหน่ง".replace(SARA_AM, "\N{THAI CHARACTER NIKHAHIT}\N{THAI CHARACTER SARA AA}")
    assert clean_text(split) == "ตำแหน่ง"
    assert clean_text("เจ้าหน้าท ี่ประสานงาน") == "เจ้าหน้าที่ประสานงาน"


def test_clean_text_strips_html_and_collapses_space():
    assert clean_text("  <b>สวัสดี</b>\n  world  ") == "สวัสดี world"
    assert clean_text(None) == ""


def test_clean_text_keeps_comparison_signs():
    assert clean_text("ค่า p < 0.05 และ n > 10") == "ค่า p < 0.05 และ n > 10"
    assert clean_text("<p>ข้อความ</p>") == "ข้อความ"


def test_repair_glyphs_keeps_space_runs():
    assert repair_glyphs("ก   B") == "ก   B"


def test_fold_and_ratio_and_key():
    assert fold_thai("รองศาสตราจารย์") == "รองศาสตราจารย"
    assert thai_ratio("ภาษาไทย") == 1.0
    assert thai_ratio("English") == 0.0
    assert thai_ratio("123 !!") == 0.0
    assert norm_key("Thai Journal, ฉบับที่ 1!") == "thaijournalฉบับที1"  # vowels kept, tone mark folded


def test_tokenize_mixed_text():
    toks = tokenize("การศึกษาผู้สูงอายุ and Long-term Care ในประเทศไทย")
    assert "การศึกษา" in toks
    assert "care" in toks
    assert "and" not in toks
    assert all(len(t) >= 2 for t in toks)


@pytest.mark.parametrize("pua", sorted(THAI_PUA))
def test_every_pua_glyph_maps_to_its_standard_code_point(pua):
    out = repair_glyphs(chr(pua))
    assert out == unicodedata.normalize("NFC", chr(THAI_PUA[pua])) and not has_pua(out)
