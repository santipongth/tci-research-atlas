"""Canonical institutions: alias table → foreign → ROR → as written; provinces named in affiliations."""
import json
import zipfile

import pytest

from atlas.countries import COUNTRIES_EN, COUNTRIES_TH, COUNTRY_ISO, COUNTRY_ISO_TH, COUNTRY_NAMES, country_of
from atlas.institutions_ref import AliasError, Resolver, inst_code, load_aliases, load_ror, type_from_name
from atlas.orgs import org_key
from atlas.places import province_finder, provinces, region_of

ALIASES = """alias,inst_id,name_th,name_en,type,province,country,ror
มหาวิทยาลัยราชภัฏเชียงราย,crru,มหาวิทยาลัยราชภัฏเชียงราย,Chiang Rai Rajabhat University,rajabhat,TH-57,TH,
Chiang Rai Rajabhat University,crru,,,,,,
มรภ.เชียงราย,crru,,,,,,
มหาวิทยาลัยเทคโนโลยีราชมงคลล้านนา,rmutl,มหาวิทยาลัยเทคโนโลยีราชมงคลล้านนา,Rajamangala University of Technology Lanna,rajamangala,TH-50,TH,
มทร.ล้านนา,rmutl,,,,,,
Bangkok University,bu,มหาวิทยาลัยกรุงเทพ,Bangkok University,university,TH-13,TH,
"""
NARESUAN_ROR = {
    "id": "https://ror.org/0abcdef12", "status": "active", "types": ["education"],
    "names": [{"value": "Naresuan University", "types": ["ror_display", "label"], "lang": "en"},
              {"value": "มหาวิทยาลัยนเรศวร", "types": ["label"], "lang": "th"},
              {"value": "NU", "types": ["acronym"], "lang": None}],
    "locations": [{"geonames_id": 1607708, "geonames_details": {"name": "Phitsanulok", "country_code": "TH",
                                                               "country_subdivision_name": "Phitsanulok"}}],
}
TOKYO_ROR = {"id": "https://ror.org/0tokyo000", "status": "active", "types": ["education"],
             "names": [{"value": "University of Tokyo", "types": ["ror_display"], "lang": "en"}],
             "locations": [{"geonames_details": {"name": "Tokyo", "country_code": "JP"}}]}


def _resolver(tmp_path, ror=()):
    p = tmp_path / "aliases.csv"
    p.write_text(ALIASES, encoding="utf-8")
    return Resolver(load_aliases(p), list(ror))


def _resolve(r, th, en=""):
    return r.resolve(th, en, org_key(th, en))


def test_provinces_are_the_77_iso_codes_with_regions():
    p = provinces()
    assert len(p) == 77 and p["TH-10"].region == "bangkok" and p["TH-38"].name_en == "Bueng Kan"
    assert {region_of(c) for c in p} == {"bangkok", "central", "northeast", "north", "south"}
    assert (region_of("TH-65"), region_of("TH-40"), region_of("TH-90"), region_of("TH-71")) == (
        "north", "northeast", "south", "central")


@pytest.mark.parametrize("th, en, code", [
    ("คณะเกษตรศาสตร์ มหาวิทยาลัยขอนแก่น", "", "TH-40"),
    ("มหาวิทยาลัยราชภัฏนครราชสีมา", "", "TH-30"),
    ("โรงพยาบาลเชียงรายประชานุเคราะห์ จ.เชียงราย", "", "TH-57"),
    ("", "Faculty of Medicine, Chiang Mai University", "TH-50"),
    ("", "Chiangmai Rajabhat University", "TH-50"),
    ("สำนักงานสาธารณสุข กรุงเทพมหานคร", "", "TH-10"),
    ("คณะครุศาสตร์ จุฬาลงกรณ์มหาวิทยาลัย", "", None),               # no province named
    ("สำนักงานเผยแพร่ความรู้", "", None),                           # แพร่ inside a word is not Phrae
])
def test_province_named_in_an_affiliation(th, en, code):
    assert province_finder().find(th, en) == code


def test_alias_table_merges_campuses_spellings_and_abbreviations(tmp_path):
    r = _resolver(tmp_path)
    a = _resolve(r, "คณะวิทยาการจัดการ มหาวิทยาลัยราชภัฏเชียงราย")
    b = _resolve(r, "", "Faculty of Education, Chiang Rai Rajabhat University, Thailand")
    c = _resolve(r, "สาขาการตลาด มรภ.เชียงราย")
    assert a == b == c and a.key == "alias:crru" and a.type == "rajabhat" and a.province == "TH-57"
    assert a.source == "alias" and a.country == "TH"
    d = _resolve(r, "มทร.ล้านนา น่าน")                 # a campus in Nan is its university (institution level)
    assert d.key == "alias:rmutl" and d.province == "TH-50" and d.type == "rajamangala"
    e = _resolve(r, "", "School of Communication Arts, Bangkok University")
    assert e.key == "alias:bu" and e.province == "TH-13"          # the alias beats "Bangkok" in the name
    assert inst_code(a.key) == "crru" and inst_code("ror:0ABCdef12") == "ror-0abcdef12"
    assert inst_code("org:abc").startswith("o") and len(inst_code("org:abc")) == 11


@pytest.mark.parametrize("body, msg", [
    ("alias,inst_id\nมหาวิทยาลัยนเรศวร,NU\n", "inst_id"),
    ("alias,inst_id,province\nมหาวิทยาลัยนเรศวร,nu,TH-99\n", "province"),
    ("alias,inst_id\nนร,nu\n", "shorter"),
    ("alias,inst_id\nมหาวิทยาลัยนเรศวร,nu\nมหาวิทยาลัยนเรศวร,cu\n", "already maps"),
    ("alias,inst_id,type\nมหาวิทยาลัยนเรศวร,nu,uni\n", "type"),
    ("alias,inst_id,colour\nx,y,z\n", "columns"),
])
def test_bad_alias_rows_stop_with_the_row(tmp_path, body, msg):
    p = tmp_path / "a.csv"
    p.write_text(body, encoding="utf-8")
    with pytest.raises(AliasError, match=msg):
        load_aliases(p)
    assert load_aliases(None) == ({}, {}) and load_aliases(tmp_path / "missing.csv") == ({}, {})


def test_ror_dump_gives_names_and_province_and_is_cached(tmp_path):
    dump = tmp_path / "ror.zip"
    with zipfile.ZipFile(dump, "w") as z:
        z.writestr("v9-ror-data_schema_v2.json", json.dumps([NARESUAN_ROR, TOKYO_ROR]))
    recs = load_ror(dump, "TH", tmp_path / "cache")
    assert [x["id"] for x in recs] == ["0abcdef12"] and recs[0]["province"] == "TH-65"
    assert (tmp_path / "cache" / "ror.TH.json").exists() and load_ror(dump, "TH", tmp_path / "cache") == recs
    r = Resolver(({}, {}), recs)
    th = _resolve(r, "คณะบริหารธุรกิจ มหาวิทยาลัยนเรศวร")
    en = _resolve(r, "", "Faculty of Business, Naresuan University")
    assert th == en and th.key == "ror:0abcdef12" and th.name_en == "Naresuan University" and th.source == "ror"
    assert _resolve(r, "", "NU").source == "name"                  # acronyms are never matched
    assert load_ror(tmp_path / "nope.zip", "TH", tmp_path / "cache") == []


def test_foreign_and_unplaced_institutions(tmp_path):
    r = _resolver(tmp_path)
    jp = _resolve(r, "", "Graduate School of Education, University of Tokyo, Japan")
    assert jp.country == "JP" and jp.province is None and jp.source == "name" and jp.key.startswith("org:")
    assert _resolve(r, "คณะศึกษาศาสตร์ มหาวิทยาลัยแห่งชาติลาว สปป.ลาว").country == "LA"
    cu = _resolve(r, "คณะครุศาสตร์ จุฬาลงกรณ์มหาวิทยาลัย")
    assert cu.country == "TH" and cu.province is None and cu.type == "university"
    assert r.resolve("", "", "") is None
    assert country_of("", "Mahidol University, Thailand") == "TH" and country_of("ภาควิชาภาษาจีน", "") is None
    assert type_from_name("โรงพยาบาลศิริราช") == "hospital" and type_from_name("Chiang Rai Rajabhat University") == "rajabhat"
    assert set(COUNTRY_ISO) == set(COUNTRIES_EN) and set(COUNTRY_ISO_TH) == set(COUNTRIES_TH)
    assert set(COUNTRY_ISO.values()) | set(COUNTRY_ISO_TH.values()) | {"TH"} <= set(COUNTRY_NAMES)


def test_province_finder_prefers_an_explicit_province_and_ignores_the_letter_cho():
    from atlas.places import province_finder

    f = province_finder()
    assert f.find("มหาวิทยาลัยสงขลานครินทร์ วิทยาเขตปัตตานี จังหวัดปัตตานี", "") == "TH-94"   # not Songkhla (TH-90)
    assert f.find("ศูนย์วิจัยเศรษฐกิจตาก", "") is None            # "…จ" of เศรษฐกิจ is not the prefix "จ." (Tak)
    assert f.find("คณะบริหารธุรกิจน่าน", "") is None
    assert f.find("สถาบันวิจัย จ. ตาก", "") == "TH-63" and f.find("โรงพยาบาลขอนแก่น จ.ขอนแก่น", "") == "TH-40"
    assert f.find("บจ.เชียงใหม่ฟู้ดส์ สำนักงานใหญ่", "") is None                 # "บจ." is a company, not "จ."
    assert f.find("ศูนย์วิจัย จังหวัดเชียงใหม่ สำนักงานจังหวัดลำพูน", "") == "TH-50"   # "…งานจังหวัด" is no marker


def test_a_thai_affiliation_ending_in_a_foreign_country_is_foreign():
    from atlas.countries import country_of, is_foreign_affiliation

    assert country_of("มหาวิทยาลัยโตเกียว ญี่ปุ่น", "") == "JP" and is_foreign_affiliation("มหาวิทยาลัยฮาร์วาร์ด สหรัฐอเมริกา", "")
    assert not is_foreign_affiliation("ภาควิชาภาษาจีน", "") and not is_foreign_affiliation("สาขา ภาษา อังกฤษ", "")
