import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from atlas.cli import app
from atlas.io_utils import read_table, write_table
from atlas.label import label
from atlas.llm import Reply
from atlas.review import REVIEW_COLUMNS, export_review, import_review, merge_candidates, suggest_merges


class FakeLLM:
    model_id = "fake-merge"

    def __init__(self, text):
        self.text, self.prompts = text, []

    def chat(self, messages):
        self.prompts.append(messages[0]["content"])
        return Reply(self.text, 0, 0, 0.0)


def _work(cfg, n_topics=6, per=4):
    """Topics 1 and 2 point the same way (near-duplicates); the others are orthogonal."""
    work = Path(cfg["pipeline"]["work_dir"])
    rng = np.random.default_rng(0)
    rows, emb, labels = [], [], []
    for t in range(1, n_topics + 1):
        axis = 0 if t in (1, 2) else t
        for i in range(per):
            v = np.eye(16)[axis] + rng.normal(0, 0.01, 16)
            emb.append(v / np.linalg.norm(v))
            rows.append({"article_id": f"a{len(rows)}", "title": f"เรื่องที่ {t}-{i}", "doc_text": "x"})
            labels.append(t)
    emb, labels = np.array(emb, dtype=np.float32), np.array(labels)
    ids = list(range(1, n_topics + 1))
    C = np.stack([emb[labels == t].mean(0) for t in ids])
    C /= np.linalg.norm(C, axis=1, keepdims=True)
    write_table(pd.DataFrame(rows), work / "02_docs.parquet")
    np.save(work / "03_embeddings.npy", emb)
    write_table(pd.DataFrame({"article_id": [r["article_id"] for r in rows], "fine_topic": labels}),
                work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"level": "fine", "topic_id": ids, "size": per, "top_terms": "ข้าว; rice",
                              "top_keywords": [f"คำ{t}; word{t}" for t in ids], "coarse_topic": 0, "coherence": 0.9}),
                work / "04_topic_info.parquet")
    np.save(work / "04_centroids.npy", C)
    (work / "04_centroid_ids.json").write_text(json.dumps(ids), encoding="utf-8")
    return work


def test_near_duplicate_pairs_go_to_the_llm_and_nothing_is_merged(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q4"
    work = _work(cfg)
    label(cfg)                                                    # provider off → keyword names
    assert [(a, b) for a, b, _ in merge_candidates(cfg)] == [(1, 2)]
    sugg = read_table(work / "05_merge_suggestions.parquet")      # the label step wrote similarity-only rows
    assert sugg["source"].tolist() == ["similarity"] and sugg["same_topic"].isna().all()
    fake = FakeLLM('{"same_topic": true, "reason": "คำถามวิจัยเดียวกัน"}')
    out = suggest_merges(cfg, llm=fake)
    assert out[["topic_a", "topic_b", "same_topic", "source"]].values.tolist() == [[1, 2, True, "llm"]]
    assert "คำ1; word1" in fake.prompts[0] and "เรื่องที่ 2-" in fake.prompts[0]
    assert sorted(read_table(work / "05_labels.parquet")["topic_id"]) == [1, 2, 3, 4, 5, 6]


def test_review_export_samples_flagged_topics_first_and_import_writes_overrides(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q4"
    cfg["review"]["sample_size"] = 4
    cfg["labeling"]["overrides_path"] = str(tmp_path / "registry" / "label_overrides.csv")
    _work(cfg)
    label(cfg)
    path = export_review(cfg)
    assert path.name == "2026Q4_label_review.csv" and path.read_bytes()[:3] == b"\xef\xbb\xbf"   # BOM for Excel
    rev = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    assert len(rev) == 4 and {"T000001", "T000002"} <= set(rev["topic_id"])
    assert rev.set_index("topic_id").loc["T000001", "possible_duplicate"].startswith("T000002")
    assert export_review(cfg).read_bytes() == path.read_bytes()                       # reproducible sample
    code = rev.loc[rev["why_in_sample"] == "random", "topic_id"].iloc[0]
    rev.loc[rev["topic_id"] == code, ["name_th_fixed", "reviewer"]] = ["ชื่อที่แก้แล้ว", "บก. ข"]
    rev.to_csv(path, index=False, encoding="utf-8-sig")
    r = import_review(cfg, path)
    assert (r["applied"], r["overrides_total"]) == (1, 1)
    out = label(cfg).set_index("topic_id")
    tid = int(code[1:])
    assert out.loc[tid, "name_th"] == "ชื่อที่แก้แล้ว" and out.loc[tid, "label_source"] == "override"
    rev2 = pd.read_csv(export_review(cfg), dtype=str, encoding="utf-8-sig")
    assert code not in set(rev2["topic_id"])                      # already fixed → not drawn again


def test_review_cli_export(make_cfg, tmp_path):
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(f"pipeline:\n  work_dir: {(tmp_path / 'work').as_posix()}\n"
                        f"  output_dir: {(tmp_path / 'out').as_posix()}\n  release: 2026Q4\n", encoding="utf-8")
    cfg = make_cfg(tmp_path)
    _work(cfg)
    label(cfg)
    r = CliRunner().invoke(app, ["review", "export", "-c", str(cfg_path)])
    assert r.exit_code == 0, r.output
    assert (tmp_path / "out" / "review" / "2026Q4_label_review.csv").exists()


def _review_csv(tmp_path, rows, name="r.csv", drop=()):
    cols = [c for c in REVIEW_COLUMNS if c not in drop]
    df = pd.DataFrame([{c: r.get(c, "") for c in cols} for r in rows], columns=cols)
    p = tmp_path / name
    df.to_csv(p, index=False, encoding="utf-8-sig")
    return p


def test_import_never_blanks_an_existing_override(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["labeling"]["overrides_path"] = str(tmp_path / "registry" / "label_overrides.csv")
    import_review(cfg, _review_csv(tmp_path, [{"topic_id": "T000001", "name_th_fixed": "ไทยแก้", "name_en_fixed": "En one",
                                               "reviewer": "a"}], "a.csv"))
    import_review(cfg, _review_csv(tmp_path, [{"topic_id": "T000001", "name_en_fixed": "En two"}], "b.csv"))
    ov = pd.read_csv(cfg["labeling"]["overrides_path"], dtype=str, encoding="utf-8-sig").fillna("")
    assert ov.loc[0, "name_th"] == "ไทยแก้" and ov.loc[0, "name_en"] == "En two" and ov.loc[0, "reviewer"] == "a"


def test_import_reports_missing_columns_and_bad_ids(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["labeling"]["overrides_path"] = str(tmp_path / "registry" / "label_overrides.csv")
    bad = _review_csv(tmp_path, [{"topic_id": "T000001"}], "m.csv", drop=("name_en_fixed",))
    with pytest.raises(ValueError, match=r"name_en_fixed.*expected columns"):
        import_review(cfg, bad)
    rows = [{"topic_id": "T000001"}, {"topic_id": "abc", "name_th_fixed": "x"}]
    with pytest.raises(ValueError, match=r"row 3: topic_id 'abc' is not T000123 or an integer"):
        import_review(cfg, _review_csv(tmp_path, rows, "i.csv"))
