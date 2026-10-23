"""Corpus format 1.0 (JSON Lines): the team's example, id rules, error rows, .gz, the Markdown parity, the schema
file, journal keys and institution hints given by the corpus."""
import gzip
import json
from pathlib import Path

import pandas as pd
import pytest

from atlas.corpus_convert import convert_markdown
from atlas.ingest import ingest, read_corpus_tables
from atlas.institutions_ref import Resolver
from atlas.io_utils import read_table
from atlas.orgs import org_key
from atlas.pipeline import STEPS, run
from atlas.registry import journal_keys
from atlas.schema.corpus import CORPUS_SCHEMA, corpus_json_schema
from atlas.sources.corpus_jsonl import parse_line

EXAMPLE = Path(__file__).resolve().parents[2] / "docs" / "corpus" / "example"
SCHEMA_FILE = Path(__file__).resolve().parents[2] / "docs" / "corpus" / "corpus.schema.json"
EXCLUDE = ("editorial", "erratum", "book-review")


def _line(**over) -> str:
    rec = {"schema": CORPUS_SCHEMA, "journal_key": "tci:j1", "year": 2022, "title": {"en": "A study of rice"}}
    rec.update(over)
    return json.dumps(rec, ensure_ascii=False)


def _corpus(tmp_path: Path, lines: list[str], name: str = "part-0001.jsonl") -> Path:
    d = tmp_path / "corpus" / "articles"
    d.mkdir(parents=True, exist_ok=True)
    data = "\n".join(lines) + "\n"
    if name.endswith(".gz"):
        with gzip.open(d / name, "wt", encoding="utf-8") as f:
            f.write(data)
    else:
        (d / name).write_text(data, encoding="utf-8")
    return tmp_path / "corpus"


def test_the_example_for_the_data_team_reads_cleanly():
    arts, auths, refs, errors, stats = read_corpus_tables(EXAMPLE, exclude=EXCLUDE)
    assert errors == []
    assert stats["excluded"] == {"editorial": 1} and stats["lines"] == 7
    assert stats["id_source"] == {"url": 3, "doi": 1, "derived": 2}
    a = arts.set_index("article_id")
    assert "so02:SampleJournal:245871" in a.index and "doi:10.5555/tmj.2023.0451" in a.index
    derived = [i for i in a.index if i.startswith("tci:")]
    assert len(derived) == 2 and all(len(i) == 20 for i in derived)
    # the undated article takes the year of the other article in its issue
    edu = a[a["journal_key"] == "tci:sample-education-journal"]
    assert edu["year"].tolist() == [2022, 2022] and sorted(edu["year_source"]) == ["given", "issue_median"]
    first = a.loc["so02:SampleJournal:245871"]
    assert first["n_authors"] == 2 and first["n_student_authors"] == 1 and first["n_references"] == 2
    one = auths[auths["article_id"] == "so02:SampleJournal:245871"]
    assert one[["position", "affiliation_index"]].values.tolist() == [[0, 0], [0, 1], [1, 0]]
    assert set(one["province"]) == {"TH-65", "TH-50"}
    assert refs.loc[refs["article_id"] == "so02:SampleJournal:245871", "translated"].tolist() == [False, False, True]


def test_derived_ids_do_not_change_between_runs():
    rec, err = parse_line(_line(), "x:1")
    again, _ = parse_line(_line(abstract={"en": "edited abstract"}), "x:2")
    assert err is None and rec["article_id"] == again["article_id"] and rec["article_id"].startswith("tci:")
    given, _ = parse_line(_line(id="tci:my-id-7", doi="10.5555/X.1"), "x:3")
    assert given["article_id"] == "tci:my-id-7" and given["id_source"] == "given"
    by_doi, _ = parse_line(_line(doi="10.5555/X.1"), "x:4")
    assert by_doi["article_id"] == "doi:10.5555/x.1"


@pytest.mark.parametrize("bad, says", [
    (_line(year=2567), "Buddhist Era"),
    (_line(abstarct={"en": "typo"}), "Extra inputs"),
    (_line(title={"th": None, "en": None}), "title needs th or en"),
    (_line(published="2023-04-15", year=2022), "differs"),
    (_line(authors=[{"name": {"en": "A"}, "affiliations": [{"name": {"en": "X"}, "province": "TH-99"}]}]), "77"),
    ('{"schema": ', "JSONDecodeError"),
])
def test_a_bad_line_is_an_error_row_not_a_crash(tmp_path, bad, says):
    root = _corpus(tmp_path, [_line(), bad, _line(title={"en": "Another study"})])
    arts, _, _, errors, stats = read_corpus_tables(root)
    assert len(arts) == 2 and len(errors) == 1 and stats["lines"] == 3
    assert errors[0]["path"].endswith("part-0001.jsonl:2") and says in errors[0]["error"]


def test_gzip_files_and_the_error_ceiling(tmp_path, make_cfg):
    root = _corpus(tmp_path, [_line(), "not json"], "part-0001.jsonl.gz")
    arts, _, _, errors, _ = read_corpus_tables(root)
    assert len(arts) == 1 and len(errors) == 1
    cfg = make_cfg(root, "corpus_jsonl")
    with pytest.raises(RuntimeError, match="max_error_ratio"):
        ingest(cfg)                                     # 1 bad line of 2 is far above the 1% ceiling


def test_an_empty_corpus_folder_is_an_error(tmp_path):
    (tmp_path / "corpus").mkdir()
    with pytest.raises(FileNotFoundError, match="articles"):
        read_corpus_tables(tmp_path / "corpus")


def test_converted_markdown_ingests_to_the_same_tables(make_cfg, thaijo_dir, tmp_path):
    conv = convert_markdown(thaijo_dir, tmp_path / "jsonl")
    assert conv["articles"] == 11 and conv["skipped"] == []
    md = make_cfg(thaijo_dir)
    ingest(md)
    want = {k: read_table(tmp_path / "work" / f"01_{k}.parquet") for k in ("articles", "authors", "references")}
    js = make_cfg(tmp_path / "jsonl", "corpus_jsonl")
    js["pipeline"]["work_dir"] = str(tmp_path / "work_js")
    ingest(js)
    got = {k: read_table(tmp_path / "work_js" / f"01_{k}.parquet") for k in ("articles", "authors", "references")}
    cols = {"articles": ["article_id", "url", "issue_url", "journal_name", "year", "doi", "title_th", "title_en",
                         "abstract_th", "abstract_en", "keywords_th", "keywords_en", "authors", "affiliations",
                         "n_authors", "n_student_authors", "n_references", "has_references", "self_citation_only"],
            "authors": ["article_id", "position", "name", "name_en", "affiliation_th", "affiliation_en", "is_student",
                        "org_key"],
            "references": ["article_id", "position", "text", "year", "lang", "translated", "self_citation"]}
    for k, c in cols.items():
        a = want[k][c].sort_values(c[:2]).reset_index(drop=True)
        b = got[k][c].sort_values(c[:2]).reset_index(drop=True)
        pd.testing.assert_frame_equal(a.astype(str), b.astype(str), obj=k)
    assert (got["articles"]["journal_key"] == "so02:BECJournal").all()


def test_full_pipeline_on_the_converted_corpus(make_cfg, thaijo_dir, tmp_path):
    convert_markdown(thaijo_dir, tmp_path / "jsonl")
    cfg = make_cfg(tmp_path / "jsonl", "corpus_jsonl")
    cfg["clustering"]["reducer"] = "pca"
    cfg["journals"]["registry_path"] = str(tmp_path / "jsonl" / "journals.csv")
    run(cfg, STEPS)
    assert json.loads((tmp_path / "out" / "atlas_data.json").read_text(encoding="utf-8"))["meta"]["total_articles"] == 11


def test_the_schema_file_for_the_team_is_up_to_date():
    assert json.loads(SCHEMA_FILE.read_text(encoding="utf-8")) == json.loads(json.dumps(corpus_json_schema())), \
        "run: uv run atlas corpus schema"


def test_a_given_journal_key_wins():
    df = pd.DataFrame({"article_id": ["so02:A:1", "doi:10.5555/x", "so02:A:2"], "journal_name": ["A", "B", "A"],
                       "journal_key": ["", "tci:b", "tci:override"]})
    assert journal_keys(df).tolist() == ["so02:A", "tci:b", "tci:override"]


def test_affiliation_hints_from_the_corpus():
    r = Resolver(({}, {}), [{"id": "0exampl00", "names": ["Some Other Name"], "name_th": "", "name_en": "Example U",
                             "type": "university", "province": "TH-50"}])
    aff = "Faculty of Science, Sample University"
    key = org_key("", aff)
    in_dump = r.resolve("", aff, key, ror="https://ror.org/0exampl00")
    assert in_dump.key == "ror:0exampl00" and in_dump.province == "TH-50" and in_dump.source == "ror"
    not_in_dump = r.resolve("", aff, key, ror="https://ror.org/0abcdef11", province="TH-65")
    assert not_in_dump.key == "ror:0abcdef11" and not_in_dump.province == "TH-65" and not_in_dump.country == "TH"
    foreign = r.resolve("", aff, key, country="JP")
    assert foreign.country == "JP" and foreign.province is None
    hinted = r.resolve("", aff, key, province="TH-40")
    assert hinted.key == f"org:{key}" and hinted.province == "TH-40"
    assert r.resolve("", aff, key).province is None        # no hint: the old rules, unchanged


def _copy_example(tmp_path: Path) -> Path:
    import shutil
    root = tmp_path / "corpus"
    shutil.copytree(EXAMPLE, root)
    return root


def test_companion_files_of_the_example_need_no_fix(tmp_path):
    from atlas.companions import check_companions
    arts, auths, _, _, _ = read_corpus_tables(EXAMPLE, exclude=EXCLUDE)
    todo = tmp_path / "todo.csv"
    c = check_companions(EXAMPLE, arts, auths, todo)
    assert c["problems"] == []
    assert c["journals"]["rows"] == 3 and c["aliases"]["covered_pct"] > 80
    assert todo.read_text(encoding="utf-8-sig").splitlines()[0].startswith("alias,inst_id,")


def test_companion_problems_are_named(tmp_path):
    from atlas.companions import check_companions
    root = _copy_example(tmp_path)
    jc = (root / "journals.csv").read_text(encoding="utf-8").splitlines()
    (root / "journals.csv").write_text("\n".join(jc[:-1]) + "\n", encoding="utf-8")        # drop one journal
    (root / "province_population.csv").write_text("code,population,year\nTH-10,5500000,2025\n", encoding="utf-8")
    arts, auths, _, _, _ = read_corpus_tables(root, exclude=EXCLUDE)
    probs = check_companions(root, arts, auths)["problems"]
    assert any("tci:sample-education-journal" in p for p in probs)
    assert any("lacks 76 province" in p for p in probs)
    (root / "institutions_aliases.csv").write_text("alias,inst_id\nSample University,Bad Id\n", encoding="utf-8")
    probs = check_companions(root, arts, auths)["problems"]
    assert any(p.startswith("aliases:") and "inst_id" in p for p in probs)


def test_a_corpus_without_journals_csv_is_flagged(tmp_path):
    from atlas.companions import check_companions
    root = _copy_example(tmp_path)
    (root / "journals.csv").unlink()
    arts, auths, _, _, _ = read_corpus_tables(root, exclude=EXCLUDE)
    assert "journals.csv is missing from the corpus folder" in check_companions(root, arts, auths)["problems"]
    assert check_companions(root, arts, auths, required=False)["problems"] == []


def test_org_names_never_carry_contact_details_or_a_bare_person():
    from atlas.orgs import org_name, publishable_name
    mail = "Independent researcher, 99/1 Moo 3, Bangkok 10400, email: somchai.j@gmail.com"
    assert publishable_name(org_name("", mail)) == ""
    assert publishable_name(org_name("นักวิชาการอิสระ 12 หมู่ 4 อีเมล somchai@gmail.com", "")) == ""
    assert publishable_name(org_name("สมชาย ใจดี", "")) == ""
    assert publishable_name(org_name("คณะบริหารธุรกิจ มหาวิทยาลัยเกษตรศาสตร์ 10900", "")) == "มหาวิทยาลัยเกษตรศาสตร์"
    assert "@" not in org_name("", "Faculty of Science, Chiang Mai University, tel 053-943-333, a@b.co")


def test_contact_labels_need_a_number_and_names_keep_their_words():
    from atlas.orgs import org_key, org_name
    assert org_name("", "Tel Aviv University") == "Tel Aviv University"
    assert org_name("", "Intel Corporation") == "Intel Corporation"
    assert org_name("สถานีโทรทัศน์ไทยพีบีเอส", "") == "สถานีโทรทัศน์ไทยพีบีเอส"
    assert org_name("", "Phra Nakhon Si Ayutthaya Rajabhat University") == "Phra Nakhon Si Ayutthaya Rajabhat University"
    assert org_name("", "Faculty of Science, Chiang Mai University, Tel. 053-943-333") == "Chiang Mai University"
    assert org_name("โรงพยาบาลเขต 9", "") == "โรงพยาบาลเขต 9" and org_key("โรงพยาบาลเขต 9", "") != org_key("โรงพยาบาลเขต 10", "")
    # one organisation, one key, whatever phone number or address the affiliation carries
    assert org_key("มหาวิทยาลัยเชียงใหม่ โทร 053-943-333", "") == org_key("มหาวิทยาลัยเชียงใหม่", "")


def test_a_network_name_takes_its_campus_but_never_a_person_or_a_number():
    from atlas.orgs import org_name
    assert org_name("วิทยาลัยพยาบาลบรมราชชนนี สุราษฎร์ธานี สถาบันพระบรมราชชนก", "") == "วิทยาลัยพยาบาลบรมราชชนนี สุราษฎร์ธานี"
    assert org_name("มหาวิทยาลัยราชภัฏ นายสมชาย", "") == "มหาวิทยาลัยราชภัฏ"
    assert org_name("มหาวิทยาลัยราชภัฏ 123 ถ.มิตรภาพ", "") == "มหาวิทยาลัยราชภัฏ"
    assert org_name("มหาวิทยาลัยราชภัฏ เชียงใหม่", "") == "มหาวิทยาลัยราชภัฏ เชียงใหม่"
