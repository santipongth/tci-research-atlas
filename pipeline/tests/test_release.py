"""Contract v2 export (→ validate → publish) on the 11 real ThaiJO files, as two releases."""
import hashlib
import json
import shutil

import pytest

from atlas.config import load_config
from atlas.io_utils import read_table
from atlas.pipeline import STEPS, run
from atlas.schema.contract import Manifest, model_for
from tests.conftest import FIXTURES


@pytest.fixture(scope="module")
def two_releases(tmp_path_factory):
    root = tmp_path_factory.mktemp("rel")
    for rel in ("2026Q1", "2026Q2"):
        cfg = load_config(None)
        cfg["pipeline"].update(work_dir=str(root / "work"), output_dir=str(root / "out"),
                               state_dir=str(root / "state"), release=rel)
        cfg["input"].update(path=str(FIXTURES / "thaijo_md"), workers=1)
        cfg["embedding"]["provider"] = "lite"
        cfg["clustering"]["reducer"] = "pca"
        run(cfg, STEPS)
    return root, cfg


def test_release_files_match_the_contract_and_link_back_to_thaijo(two_releases):
    root, _ = two_releases
    data = root / "out" / "data"
    assert json.loads((data / "latest.json").read_text(encoding="utf-8"))["release"] == "2026Q2"
    man = Manifest.model_validate_json((data / "2026Q2" / "manifest.json").read_text(encoding="utf-8"))
    assert man.previous_release == "2026Q1" and {f.path for f in man.files} >= {
        "overview.json", "taxonomy.json", "topics.json", "series.json", "edges.json", "keywords.json"}
    for f in man.files:
        raw = (data / "2026Q2" / f.path).read_bytes()
        assert len(raw) == f.bytes and hashlib.sha256(raw).hexdigest() == f.sha256
        model_for(f.path).model_validate_json(raw)
    topics = json.loads((data / "2026Q2" / "topics.json").read_text(encoding="utf-8"))["topics"]
    assert all(t["status"] == "LOW_DATA" and t["id"].startswith("T") for t in topics)
    assert topics[0]["lineage"]["born"] == "2026Q1" and topics[0]["lineage"]["event"] == "continue"
    assert all(t["metrics"]["low_data_reason"] in ("few_articles", "not_estimable") for t in topics)
    assert man.definition_version == 3 and man.ci_level == 0.9 and man.embedding_provider == "lite"
    assert man.labels.provider == "off" and man.labels.keywords == len(topics) and man.llm == []
    ov = json.loads((data / "2026Q2" / "overview.json").read_text(encoding="utf-8"))
    assert ov["brief"]["source"] == "template" and ov["definition_version"] == 3
    detail = json.loads((data / "2026Q2" / f"topics/{topics[0]['id']}.json").read_text(encoding="utf-8"))
    assert detail["articles"][0]["url"].startswith("https://so02.tci-thaijo.org/")
    blob = "".join(p.read_text(encoding="utf-8") for p in (data / "2026Q2").rglob("*.json"))
    docs = read_table(root / "work" / "02_docs.parquet")
    snippets = [a[:40] for a in list(docs["abstract_th"]) + list(docs["abstract_en"]) if len(a) >= 40]
    assert snippets and not any(s in blob for s in snippets)     # abstracts are never published
    tax = json.loads((data / "2026Q2" / "taxonomy.json").read_text(encoding="utf-8"))
    assert tax["source"] == "agglomerative" and all(g["color"].startswith("cat-") for g in tax["groups"])


def _copy(two_releases, tmp_path):
    root, cfg = two_releases
    dst = tmp_path / "data"
    shutil.copytree(root / "out" / "data", dst)
    return dst, cfg


def test_group_codes_never_mistake_a_fallback_group_for_an_openalex_field():
    from atlas.export_v2 import group_code
    from atlas.taxonomy import FALLBACK_GROUP_BASE

    assert group_code(33, "openalex") == "F33" and group_code(3, "agglomerative") == "G03"
    assert group_code(FALLBACK_GROUP_BASE + 5, "openalex") == "G05"


def test_no_published_group_has_an_empty_name_even_on_a_stale_taxonomy(two_releases, tmp_path, capsys):
    import pandas as pd

    from atlas.export_v2 import build_release
    from atlas.io_utils import write_table
    from atlas.taxonomy import FALLBACK_GROUP_EN, FALLBACK_GROUP_TH, TAXONOMY_COLUMNS

    root, cfg = two_releases
    for g in json.loads((root / "out" / "data" / "2026Q2" / "taxonomy.json").read_text(encoding="utf-8"))["groups"]:
        assert g["th"].strip() and g["en"].strip()
    work = tmp_path / "work"
    shutil.copytree(root / "work", work)
    info = read_table(work / "04_topic_info.parquet")
    write_table(pd.DataFrame([{"topic_id": 999, "group_id": 17, "group_en": "Computer Science", "group_th": "ก",
                               "subfield_id": "1702", "subfield_en": "AI", "vote_share": 0.9, "cross_field": False,
                               "source": "openalex"}], columns=TAXONOMY_COLUMNS), work / "10_taxonomy.parquet")
    files = build_release({**cfg, "pipeline": {**cfg["pipeline"], "work_dir": str(work)}})
    assert "WARNING" in capsys.readouterr().out                  # stale taxonomy: every topic falls back
    groups = files["taxonomy.json"].groups
    coarse = sorted({int(c) for c in info["coarse_topic"]})
    assert files["taxonomy.json"].source == "openalex"
    assert {g.id for g in groups} == {f"G{c:02d}" for c in coarse}  # never F<coarse>: not an OpenAlex field
    assert {(g.th, g.en) for g in groups} == {(FALLBACK_GROUP_TH.format(n=c), FALLBACK_GROUP_EN.format(n=c))
                                              for c in coarse}
    assert all(g.th.strip() and g.en.strip() for g in groups)
    assert {t.group for t in files["topics.json"].topics} <= {g.id for g in groups}
