import shutil

import pandas as pd

from atlas.ingest import ingest
from atlas.io_utils import read_table
from atlas.orgs import org_key
from atlas.thai import norm_key


def test_org_key_prefers_university_level():
    # keys are norm_key()-folded (tone marks / thanthakhat removed) so spelling variants of marks collapse
    assert org_key("สาขาบริหารธุรกิจ คณะบริหารธุรกิจ เศรษฐศาสตร์และการสื่อสาร มหาวิทยาลัยนเรศวร", "") == "มหาวิทยาลัยนเรศวร"
    assert org_key("วิทยาลัยพาณิชยศาสตร์ มหาวิทยาลัยบูรพา", "") == "มหาวิทยาลัยบูรพา"
    assert org_key("คณะนิเทศศาสตร์ สถาบันบัณฑิตพัฒนบริหารศาสตร์", "") == norm_key("สถาบันบัณฑิตพัฒนบริหารศาสตร์")
    assert org_key("", "Faculty of Business, Economics and Communications, Naresuan University") == "naresuanuniversity"
    assert org_key("", "") == ""
    assert org_key("ศูนย์ถ่ายทอดองค์ความรู้ ภูมิปัญญาและนวัตกรรมชุมชน", "") != ""


def test_ingest_real_fixtures(make_cfg, thaijo_dir):
    cfg = make_cfg(thaijo_dir)
    df = ingest(cfg)
    work = cfg["pipeline"]["work_dir"]
    assert len(df) == 11 and df["article_id"].is_unique
    assert df["year"].notna().all()
    row = df.set_index("article_id").loc["so02:BECJournal:54895"]
    assert (int(row["year"]), row["year_source"]) == (2014, "doi")
    assert "; " in row["keywords_th"]
    authors = read_table(f"{work}/01_authors.parquet")
    refs = read_table(f"{work}/01_references.parquet")
    assert len(authors) == 21
    assert len(refs) == 32
    # 9 authors carry a Thai Naresuan affiliation; the English-only one maps to "naresuanuniversity"
    assert authors["org_key"].eq("มหาวิทยาลัยนเรศวร").sum() == 9
    assert authors["org_key"].eq("naresuanuniversity").sum() == 1


def test_duplicate_file_is_dropped(make_cfg, thaijo_dir, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    for name in ("so02_BECJournal_54895.md", "so02_BECJournal_62642.md"):
        shutil.copyfile(thaijo_dir / name, src / name)
    shutil.copyfile(thaijo_dir / "so02_BECJournal_54895.md", src / "copy_of_tqa.md")
    assert len(ingest(make_cfg(src))) == 2


def test_missing_url_gets_stable_unique_file_id(make_cfg, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    for i in (1, 2):
        (src / f"broken{i}.md").write_text(f"# ชื่อเรื่องที่ {i} สำหรับทดสอบระบบ\n\n**Published:** 2020-01-0{i}\n", encoding="utf-8")
    ids1 = sorted(ingest(make_cfg(src))["article_id"])
    ids2 = sorted(ingest(make_cfg(src))["article_id"])
    assert ids1 == ids2 and len(set(ids1)) == 2 and all(i.startswith("file:") for i in ids1)


def test_thai_filename_is_read(make_cfg, thaijo_dir, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    shutil.copyfile(thaijo_dir / "so02_BECJournal_74136.md", src / "อุปสรรคต่อการนำพาณิชย์อิเล็กทรอนิกส์.md")
    assert ingest(make_cfg(src))["article_id"].tolist() == ["so02:BECJournal:74136"]


def test_table_input_converts_buddhist_years_and_filters(make_cfg, tmp_path):
    csv = tmp_path / "t.csv"
    pd.DataFrame({"id": ["a", "b", "c"], "title_th": ["หนึ่ง", "สอง", "สาม"],
                  "year": ["2560", "2018", "1800"]}).to_csv(csv, index=False)
    df = ingest(make_cfg(csv, "table")).set_index("article_id")
    assert int(df.loc["a", "year"]) == 2017 and int(df.loc["b", "year"]) == 2018
    assert "c" not in df.index


def test_dedup_keeps_most_complete_record(make_cfg, tmp_path):
    csv = tmp_path / "t.csv"
    pd.DataFrame({"id": ["x1", "x2"], "title_th": ["ชื่อเดียวกัน", "ชื่อเดียวกัน"],
                  "abstract_th": ["", "มีบทคัดย่อ"], "doi": ["10.1/abc", "10.1/ABC"],
                  "year": ["2020", "2020"]}).to_csv(csv, index=False)
    df = ingest(make_cfg(csv, "table"))
    assert df["article_id"].tolist() == ["x2"]


# ---- F7: DOI dedup must not drop distinct articles; duplicate ids are always dropped
def test_same_doi_different_titles_are_both_kept_and_counted(make_cfg, tmp_path):
    from atlas.ingest import add_convenience_columns, dedup

    csv = tmp_path / "t.csv"
    pd.DataFrame({"id": ["y1", "y2", "y3"],
                  "title_en": ["Rice yield under drought", "Tourism in Nan province", "Rice yield under drought!"],
                  "doi": ["10.1/shared", "10.1/SHARED", "10.1/shared "], "year": ["2020", "2020", "2021"]}
                 ).to_csv(csv, index=False)
    df = ingest(make_cfg(csv, "table"))
    assert sorted(df["article_id"]) == ["y1", "y2"]              # y3 = same DOI + same normalised title
    raw = add_convenience_columns(pd.DataFrame({
        "article_id": ["a", "b"], "title_th": ["", ""], "title_en": ["One title here", "Another title"],
        "abstract_th": "", "abstract_en": "", "keywords_th": "", "keywords_en": "", "doi": ["10.9/x", "10.9/x"],
        "authors": "", "year": [2020, 2020]}))
    out, stats = dedup(raw)
    assert len(out) == 2 and stats == {"dropped": 0, "doi_title_conflicts": 1}


def test_duplicate_article_ids_are_dropped_even_with_dedup_off(make_cfg, tmp_path):
    csv = tmp_path / "t.csv"
    pd.DataFrame({"id": ["d1", "d1", "d2"], "title_en": ["Same paper", "Same paper", "Other paper"],
                  "abstract_en": ["", "has an abstract", ""], "year": ["2020", "2020", "2020"]}
                 ).to_csv(csv, index=False)
    cfg = make_cfg(csv, "table")
    cfg["input"]["dedup"]["enabled"] = False
    df = ingest(cfg).set_index("article_id")
    assert sorted(df.index) == ["d1", "d2"]
    assert df.loc["d1", "abstract_en"] == "has an abstract"      # the most complete record is kept

