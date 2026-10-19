"""Step institutions: canonical institutions, network, provinces, R6 — aggregates only (PDPA)."""
import json
from pathlib import Path

import pandas as pd
import pytest

from atlas.institutions import institutions, suggest
from atlas.io_utils import read_table, write_table
from atlas.orgs import org_key
from atlas.pipeline import STEPS
from tests.p2_work import CU, TOKYO, make_p2_work

PEOPLE = ("สมชาย ใจดี", "สุดา ศรีสุข")


def _work(tmp_path):
    """p2 work + an alias for Naresuan, Chula co-authors on six J1 articles of 2020+, one Tokyo co-author in W."""
    cfg = make_p2_work(tmp_path)
    work = Path(cfg["pipeline"]["work_dir"])
    aliases = tmp_path / "aliases.csv"
    aliases.write_text("alias,inst_id,name_th,name_en,type,province\n"
                       "มหาวิทยาลัยนเรศวร,nu,มหาวิทยาลัยนเรศวร,Naresuan University,university,TH-65\n", encoding="utf-8")
    cfg["institutions"]["aliases_path"] = str(aliases)
    arts = read_table(work / "01_articles.parquet")
    recent = arts[(arts["journal_name"] == "J1") & (arts["year"] >= 2020)]["article_id"].tolist()
    extra = [{"article_id": a, "position": 5, "affiliation_th": CU, "affiliation_en": "", "org_key": org_key(CU, "")}
             for a in recent[:6]]
    extra.append({"article_id": recent[0], "position": 6, "affiliation_th": "", "affiliation_en": TOKYO,
                  "org_key": org_key("", TOKYO)})
    authors = read_table(work / "01_authors.parquet").assign(name=PEOPLE[0])
    write_table(pd.concat([authors, pd.DataFrame(extra).assign(name=PEOPLE[1])], ignore_index=True),
                work / "01_authors.parquet")
    return cfg, work


def test_institutions_resolve_publish_pair_and_place(tmp_path):
    cfg, work = _work(tmp_path)
    inst = institutions(cfg).set_index("inst_key")
    nu = inst.loc["alias:nu"]
    assert nu["province"] == "TH-65" and nu["source"] == "alias" and bool(nu["published"]) and nu["code"] == "nu"
    tokyo = inst.loc[f"org:{org_key('', TOKYO)}"]
    assert tokyo["country"] == "JP" and not bool(tokyo["published"])          # 1 article in W < min_articles
    pairs = read_table(work / "15_inst_pairs.parquet")
    assert len(pairs) == 1 and set(pairs.iloc[0][["a", "b"]]) == {"alias:nu", f"org:{org_key(CU, '')}"}
    assert pairs.iloc[0]["articles"] >= cfg["institutions"]["network_min_articles"]
    meta = json.loads((work / "15_institutions_meta.json").read_text(encoding="utf-8"))
    assert meta["with_org"] == 56 and meta["pct_international"] == pytest.approx(1 / 56, abs=1e-6)
    assert meta["institutions_total"] == len(inst) and meta["windows"]["W"] == [2020, 2024]
    prov = read_table(work / "15_provinces.parquet").set_index("code")
    assert prov.loc["TH-65", "articles"] == nu["articles"] and "TH-10" not in prov.index
    countries = read_table(work / "15_inst_countries.parquet")
    assert countries[countries["inst_key"] == ""].set_index("country")["articles"].to_dict() == {"JP": 1}
    assert STEPS.index("match") < STEPS.index("institutions") < STEPS.index("export")


def test_no_person_column_and_small_units_stay_internal(tmp_path):
    cfg, work = _work(tmp_path)
    institutions(cfg)
    tokyo = f"org:{org_key('', TOKYO)}"
    for p in work.glob("15_*"):
        if p.suffix == ".json":
            blob = p.read_text(encoding="utf-8")
        else:
            table = read_table(p.with_suffix(".parquet"))
            assert not {"name", "position", "role", "is_student"} & set(table.columns), p.name
            blob = table.astype(str).to_csv()
            if p.stem != "15_institutions" and p.stem != "15_article_institutions":
                assert tokyo not in blob, p.name                       # unpublished: in totals only
        assert not any(person in blob for person in PEOPLE), p.name


def test_suggestions_skip_partners_and_need_similar_topics():
    mix = pd.DataFrame({"inst_key": ["a", "a", "b", "b", "c", "d"], "topic_id": [1, 2, 1, 2, 1, 3],
                        "count": [5, 5, 4, 6, 9, 9], "share": [0.5, 0.5, 0.4, 0.6, 1.0, 1.0]})
    out = suggest(mix, coauthored={("a", "b")}, k=2, min_sim=0.3)
    got = {(r.inst_key, r.other_key) for r in out.itertuples()}
    assert ("a", "b") not in got and ("a", "c") in got and ("a", "d") not in got   # partners and unrelated skipped
    assert out.set_index(["inst_key", "other_key"]).loc[("a", "c"), "topics"] == "1"
