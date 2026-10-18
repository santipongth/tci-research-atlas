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


# ---- F11: a file that cannot be read or parsed is recorded and skipped, never aborts the run
def test_parser_failure_is_recorded_and_skipped(make_cfg, thaijo_dir, tmp_path, monkeypatch):
    import atlas.ingest as ing

    src = tmp_path / "in"
    src.mkdir()
    for name in ("so02_BECJournal_54895.md", "so02_BECJournal_62642.md"):
        shutil.copyfile(thaijo_dir / name, src / name)
    real = ing.parse_markdown

    def flaky(text, source_path=""):
        if source_path.endswith("62642.md"):
            raise IndexError("parser bug on this layout")
        return real(text, source_path=source_path)
    monkeypatch.setattr(ing, "parse_markdown", flaky)
    cfg = make_cfg(src)
    cfg["input"]["max_error_ratio"] = 0.6            # 1 of 2 files fails: allow it deliberately
    df = ingest(cfg)
    assert df["article_id"].tolist() == ["so02:BECJournal:54895"]
    errs = read_table(tmp_path / "work" / "01_ingest_errors.parquet")
    assert len(errs) == 1 and errs.loc[0, "path"].endswith("62642.md")
    assert errs.loc[0, "error"] == "IndexError: parser bug on this layout"


def test_unreadable_path_is_recorded_with_a_process_pool(thaijo_dir, tmp_path, monkeypatch):
    import atlas.ingest as ing

    shutil.copyfile(thaijo_dir / "so02_BECJournal_54895.md", tmp_path / "good.md")
    (tmp_path / "bad.md").mkdir()                    # matches the glob, cannot be read as a file
    monkeypatch.setattr(ing, "POOL_MIN_FILES", 0)    # force the ProcessPoolExecutor path
    recs, errors = ing.read_thaijo_corpus(tmp_path, workers=2)
    assert [r["article_id"] for r in recs] == ["so02:BECJournal:54895"]
    assert len(errors) == 1 and errors[0]["path"].endswith("bad.md")
    assert errors[0]["error"].split(":")[0] in {"IsADirectoryError", "PermissionError"}


def test_invalid_utf8_is_kept_with_decode_replaced_flag(make_cfg, thaijo_dir, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    raw = (thaijo_dir / "so02_BECJournal_54895.md").read_bytes()
    (src / "broken_bytes.md").write_bytes(raw.replace(b"## Abstract\n", b"## Abstract\n\x80\x81 ", 1))
    shutil.copyfile(thaijo_dir / "so02_BECJournal_62642.md", src / "clean.md")
    df = ingest(make_cfg(src)).set_index("article_id")
    assert "decode_replaced" in df.loc["so02:BECJournal:54895", "text_quality"]
    assert "decode_replaced" not in df.loc["so02:BECJournal:62642", "text_quality"]
    assert len(read_table(tmp_path / "work" / "01_ingest_errors.parquet")) == 0


# ---- Task 20 item 1: per-file error ceiling (input.max_error_ratio)
def _md_corpus(root, n_good: int, n_bad: int):
    root.mkdir(parents=True, exist_ok=True)
    for i in range(n_good):
        (root / f"g{i}.md").write_text(
            f"# Paper number {i}\n\n**Journal:** J\n**Published:** 2020-01-01\n"
            f"**Article URL:** https://so01.tci-thaijo.org/index.php/J/article/view/{i}\n\n"
            f"## Abstract\n\nAn English abstract {i}.\n", encoding="utf-8")
    for i in range(n_bad):
        (root / f"bad{i}.md").mkdir()                # matches the glob, cannot be read as a file


def test_error_ratio_below_ceiling_passes(make_cfg, tmp_path):
    _md_corpus(tmp_path / "in", 199, 1)              # 1 bad of 200 = 0.5% <= 1%
    df = ingest(make_cfg(tmp_path / "in"))
    assert len(df) == 199


def test_error_ratio_above_ceiling_raises_after_writing_errors(make_cfg, tmp_path):
    import pytest

    _md_corpus(tmp_path / "in", 95, 5)               # 5 of 100 = 5% > 1%
    with pytest.raises(RuntimeError) as ei:
        ingest(make_cfg(tmp_path / "in"))
    msg = str(ei.value)
    assert "0.05" in msg and "0.01" in msg and "01_ingest_errors" in msg and "max_error_ratio" in msg
    assert "IsADirectoryError" in msg or "PermissionError" in msg
    assert len(read_table(tmp_path / "work" / "01_ingest_errors.parquet")) == 5     # inspectable


def test_all_files_failing_raises(make_cfg, tmp_path):
    import pytest

    _md_corpus(tmp_path / "in", 0, 3)
    with pytest.raises(RuntimeError, match="01_ingest_errors"):
        ingest(make_cfg(tmp_path / "in"))
    assert len(read_table(tmp_path / "work" / "01_ingest_errors.parquet")) == 3


def test_error_ceiling_is_configurable(make_cfg, tmp_path):
    _md_corpus(tmp_path / "in", 95, 5)
    cfg = make_cfg(tmp_path / "in")
    cfg["input"]["max_error_ratio"] = 0.10
    assert len(ingest(cfg)) == 95


def test_error_ratio_config_is_validated():
    import pytest

    from atlas.config import AtlasConfig

    assert AtlasConfig().input.max_error_ratio == 0.01
    with pytest.raises(ValueError):
        AtlasConfig.model_validate({"input": {"max_error_ratio": 1.5}})


# ---- Task 20 item 2: same DOI, one-sided / partly different titles
def _dedup_frame(rows):
    from atlas.ingest import add_convenience_columns

    base = {"title_th": "", "title_en": "", "abstract_th": "", "abstract_en": "", "keywords_th": "",
            "keywords_en": "", "doi": "10.9/x", "authors": "", "year": 2020}
    return add_convenience_columns(pd.DataFrame([{**base, **r} for r in rows]))


def test_same_doi_same_english_title_one_copy_missing_thai_is_deduped():
    from atlas.ingest import dedup

    th = "\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER KHO KHUAT}"
    out, stats = dedup(_dedup_frame([
        {"article_id": "a", "title_th": th, "title_en": "Rice yield under drought"},
        {"article_id": "b", "title_th": "", "title_en": "Rice yield under drought"}]))
    assert out["article_id"].tolist() == ["a"] and stats == {"dropped": 1, "doi_title_conflicts": 0}


def test_same_doi_different_thai_and_english_titles_are_kept_and_counted():
    from atlas.ingest import dedup

    th1 = "\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER KHO KHAI}"
    th2 = "\N{THAI CHARACTER KHO KHUAT}\N{THAI CHARACTER KHO KHWAI}"
    out, stats = dedup(_dedup_frame([
        {"article_id": "a", "title_th": th1, "title_en": "Rice yield"},
        {"article_id": "b", "title_th": th2, "title_en": "Tourism in Nan"}]))
    assert sorted(out["article_id"]) == ["a", "b"] and stats == {"dropped": 0, "doi_title_conflicts": 1}


def test_same_doi_same_thai_title_different_english_is_deduped_keeping_most_complete():
    from atlas.ingest import dedup

    th = "\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER KHO KHUAT}"
    out, stats = dedup(_dedup_frame([
        {"article_id": "a", "title_th": th, "title_en": "Rice yield"},
        {"article_id": "b", "title_th": th, "title_en": "Rice yield under drought", "abstract_en": "has one"}]))
    assert out["article_id"].tolist() == ["b"] and stats == {"dropped": 1, "doi_title_conflicts": 0}


def test_dedup_beyond_first_80_chars_of_thai_title_via_english_key():
    from atlas.ingest import dedup

    th_a = "\N{THAI CHARACTER KO KAI}" * 90 + "\N{THAI CHARACTER KHO KHAI}"
    th_b = "\N{THAI CHARACTER KO KAI}" * 90 + "\N{THAI CHARACTER KHO KHUAT}"       # same first 80, differ later
    out, _ = dedup(_dedup_frame([
        {"article_id": "a", "title_th": th_a, "title_en": "Same english"},
        {"article_id": "b", "title_th": th_b, "title_en": "Same english"}]))
    assert len(out) == 1
