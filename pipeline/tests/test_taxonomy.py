import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.export import build_atlas
from atlas.io_utils import read_table, write_table
from atlas.synth import SUBFIELDS, TOPICS, reference_works
from atlas.taxonomy import FALLBACK_GROUP_BASE, FIELD_TH, knn_vote, load_topic_groups, taxonomy

KEYS = ["genai_edu", "math_learning", "print_media"]


def test_knn_vote_weights_by_similarity():
    ref = np.eye(3, dtype=np.float32)
    labels = np.array(["a", "b", "b"])
    q = np.array([[0.9, 0.1, 0.0]], dtype=np.float32)
    pred, conf = knn_vote(q / np.linalg.norm(q), ref, labels, k=3)
    assert pred.tolist() == ["a"] and 0.5 < conf[0] < 1.0


def _corpus(cfg, n_per=40):
    """Three planted topics, docs written from the synthetic topic vocabularies, topic ids 1..3."""
    rng = np.random.default_rng(0)
    by_key = {t[0]: t for t in TOPICS}
    rows, labels = [], []
    for tid, key in enumerate(KEYS, start=1):
        _, _, th, en = by_key[key]
        for i in range(n_per):
            words = list(rng.choice(en, 4, replace=False)) + list(rng.choice(th, 2, replace=False))
            rows.append({"article_id": f"{key}{i}", "doc_text": " . ".join(words)})
            labels.append(tid)
    work = Path(cfg["pipeline"]["work_dir"])
    n = len(rows)
    write_table(pd.DataFrame(rows), work / "02_docs.parquet")
    write_table(pd.DataFrame({"article_id": [r["article_id"] for r in rows], "fine_topic": labels}),
                work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"topic_id": [1, 2, 3], "size": n_per, "coarse_topic": [0, 0, 1]}),
                work / "04_topic_info.parquet")
    np.save(work / "03_embeddings.npy", np.random.default_rng(1).normal(size=(n, 8)).astype(np.float32))
    (work / "04_centroid_ids.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    ref = Path(cfg["pipeline"]["work_dir"]).parent / "ref.jsonl"
    ref.write_text("\n".join(json.dumps(w) for w in reference_works(n_per_topic=20)), encoding="utf-8")
    return ref


def test_topics_are_anchored_to_openalex_subfields(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["embedding"]["provider"] = "lite"            # lite vectors are fitted jointly with the reference
    cfg["taxonomy"]["reference_path"] = str(_corpus(cfg))
    out = taxonomy(cfg).set_index("topic_id")
    for tid, key in enumerate(KEYS, start=1):
        sid, _, fid, fname = SUBFIELDS[key]
        assert (out.loc[tid, "subfield_id"], out.loc[tid, "group_id"]) == (sid, int(fid))
        assert out.loc[tid, "group_th"] == FIELD_TH[fid] and out.loc[tid, "group_en"] == fname
    assert not out["cross_field"].any() and set(out["source"]) == {"openalex"}
    meta = json.loads((tmp_path / "work" / "10_taxonomy_meta.json").read_text(encoding="utf-8"))
    assert meta["source"] == "openalex" and meta["n_reference"] == 320 and meta["holdout_accuracy_field"] >= 0.9
    assert load_topic_groups(tmp_path / "work").set_index("topic_id")["group_id"].to_dict() == {1: 17, 2: 33, 3: 33}


def test_mixed_topic_is_flagged_cross_field(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["embedding"]["provider"] = "lite"            # lite vectors are fitted jointly with the reference
    cfg["taxonomy"]["reference_path"] = str(_corpus(cfg))
    fine = read_table(tmp_path / "work" / "04_fine_topics.parquet")
    num = fine["article_id"].str.extract(r"(\d+)$")[0].astype(int)
    key = fine["article_id"].str.replace(r"\d+$", "", regex=True)
    fine["fine_topic"] = 3
    fine.loc[(key == "math_learning") & (num >= 20), "fine_topic"] = 2
    fine.loc[((key != "print_media") & (num < 20)) | ((key == "print_media") & (num < 15)), "fine_topic"] = 1
    write_table(fine, tmp_path / "work" / "04_fine_topics.parquet")     # topic 1 = 20 AI + 20 maths + 15 print
    out = taxonomy(cfg).set_index("topic_id")
    assert bool(out.loc[1, "cross_field"]) and out.loc[1, "vote_share"] < 0.5 + 1e-9


def test_no_reference_falls_back_to_agglomerative_groups(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["embedding"]["provider"] = "lite"            # lite vectors are fitted jointly with the reference
    _corpus(cfg)                                       # reference_path unset + ATLAS_OFFLINE=1 → no OpenAlex
    out = taxonomy(cfg)
    assert set(out["source"]) == {"agglomerative"} and out["group_id"].tolist() == [0, 0, 1]
    meta = json.loads((tmp_path / "work" / "10_taxonomy_meta.json").read_text(encoding="utf-8"))
    assert meta["source"] == "agglomerative" and "ATLAS_OFFLINE" in meta["reason"]
    cfg["taxonomy"]["source"] = "off"
    assert set(taxonomy(cfg)["source"]) == {"agglomerative"}


def test_api_provider_embeds_reference_through_the_store(make_cfg, tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    cfg["taxonomy"]["reference_path"] = str(_corpus(cfg))
    cfg["embedding"]["provider"] = "api"
    seen = {}

    def fake_embed_texts(cfg_, texts):
        seen["n"] = len(texts)
        return np.random.default_rng(2).normal(size=(len(texts), 8)).astype(np.float32)

    monkeypatch.setattr("atlas.taxonomy.embed_texts", fake_embed_texts)
    taxonomy(cfg)
    assert seen["n"] == 320


def test_v11_export_uses_field_names_for_groups():
    info = pd.DataFrame({"topic_id": [1, 2], "size": [30, 10], "top_terms": "a", "top_keywords": "a",
                         "coarse_topic": [33, 33], "coherence": 0.9})
    labels = pd.DataFrame({"level": "fine", "topic_id": [1, 2], "name_th": ["หนึ่ง", "สอง"], "name_en": ["One", "Two"],
                           "description": "", "keywords": "", "cache_key": "x"})
    layout = pd.DataFrame([{"kind": "group", "id": 33, "x": 1.0, "y": 1.0, "r": 5.0, "parent": -1},
                           {"kind": "topic", "id": 1, "x": 1.0, "y": 1.0, "r": 3.0, "parent": 33},
                           {"kind": "topic", "id": 2, "x": 2.0, "y": 2.0, "r": 2.0, "parent": 33}])
    em = pd.DataFrame({"topic_id": [1, 2], "status": "STABLE", "emerging_score": 50.0, "cagr_recent": 0.0,
                       "burst_years": "", "share_growth": 0.0, "share_growth_lo": 0.0, "share_growth_hi": 0.0,
                       "n_journals_R": 3, "n_orgs_R": 3, "journal_driven": False, "orgs_unverified": False})
    atlas = build_atlas(info, labels, layout, pd.DataFrame(columns=["s", "t", "w"]), em, pd.DataFrame(),
                        {"last_complete_year": 2024}, 40, True, 3,
                        group_names={33: ("สังคมศาสตร์", "Social Sciences")})
    assert atlas["groups"][0]["th"] == "สังคมศาสตร์" and atlas["groups"][0]["id"] == "g33"


def test_stale_taxonomy_never_drops_topics_and_export_matches_layout(make_cfg, tmp_path, capsys):
    """10_taxonomy from before a re-cluster knows topics {1, 2}; 04_topic_info has {1, 2, 3}."""
    from atlas.export import export
    from atlas.forecast import FORECAST_COLUMNS
    from atlas.layout import layout

    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q1"
    cfg["layout"]["galaxy"] = False
    cfg["export"]["v2"] = False                  # checks atlas_data.json 1.1 (the minimal work_dir has no embeddings)
    work = tmp_path / "work"
    write_table(pd.DataFrame({"topic_id": [1, 2, 3], "size": [30, 20, 10], "coarse_topic": [0, 0, 5],
                              "top_terms": "", "top_keywords": "", "coherence": 0.5}), work / "04_topic_info.parquet")
    write_table(pd.DataFrame({"topic_id": [1, 2], "group_id": [17, 33], "group_en": ["Computer Science", "Social Sciences"],
                              "group_th": [FIELD_TH["17"], FIELD_TH["33"]]}), work / "10_taxonomy.parquet")
    np.save(work / "04_centroids.npy", np.eye(3, 8, dtype=np.float32))
    (work / "04_centroid_ids.json").write_text("[1, 2, 3]", encoding="utf-8")
    assert load_topic_groups(work).set_index("topic_id")["group_id"].to_dict() == {1: 17, 2: 33, 3: FALLBACK_GROUP_BASE + 5}
    assert "WARNING" in capsys.readouterr().out

    layout(cfg)
    lay = read_table(work / "09_layout.parquet")
    assert lay[lay["kind"] == "topic"].set_index("id")["parent"].to_dict() == {1: 17, 2: 33, 3: FALLBACK_GROUP_BASE + 5}
    write_table(pd.DataFrame({"article_id": range(60)}), work / "02_docs.parquet")
    write_table(pd.DataFrame({"level": "fine", "topic_id": [1, 2, 3], "name_th": ["a", "b", "c"],
                              "name_en": ["A", "B", "C"], "description": "", "keywords": "", "cache_key": "x"}),
                work / "05_labels.parquet")
    write_table(pd.DataFrame({"topic_id": [1, 2, 3], "status": "STABLE", "emerging_score": 10.0, "cagr_recent": 0.0,
                              "burst_years": "", "share_growth": 0.0, "share_growth_lo": -0.1, "share_growth_hi": 0.1,
                              "n_journals_R": 3, "n_orgs_R": 3, "journal_driven": False, "orgs_unverified": False}),
                work / "07_emerging.parquet")
    write_table(pd.DataFrame(columns=FORECAST_COLUMNS), work / "08_forecasts.parquet")
    (work / "06_meta.json").write_text(json.dumps({"last_complete_year": 2024, "as_of_year": 2026,
                                                   "trimmed_years": []}), encoding="utf-8")
    export(cfg)
    atlas = json.loads((tmp_path / "out" / "atlas_data.json").read_text(encoding="utf-8"))
    groups = {n["nodeId"]: n["group"] for n in atlas["nodes"] if n["kind"] == "topic"}
    assert groups == {"t1": "g17", "t2": "g33", "t3": "g1005"}                 # same group ids as the layout
    assert atlas["meta"]["total_topics"] == 3 and {g["id"] for g in atlas["groups"]} == {"g17", "g33", "g1005"}


def test_fallback_group_never_collides_with_an_openalex_field(tmp_path):
    work = tmp_path / "work"
    write_table(pd.DataFrame({"topic_id": [1, 2, 3], "size": [30, 20, 10], "coarse_topic": [0, 0, 17],
                              "top_terms": "", "top_keywords": "", "coherence": 0.5}), work / "04_topic_info.parquet")
    write_table(pd.DataFrame({"topic_id": [1, 2], "group_id": [17, 33], "group_en": ["Computer Science", "Social"],
                              "group_th": [FIELD_TH["17"], FIELD_TH["33"]]}), work / "10_taxonomy.parquet")
    out = load_topic_groups(work).set_index("topic_id")
    g = out["group_id"].to_dict()
    assert g[3] != g[1] and g[3] >= FALLBACK_GROUP_BASE            # coarse 17 is not OpenAlex field 17
    assert (out.loc[3, "group_th"], out.loc[3, "group_en"]) == ("ยังไม่จัดสาขา (กลุ่ม 17)", "Unmapped group 17")
