import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.label import label, label_job, load_overrides, representative_indices
from atlas.llm import Reply


class FakeLLM:
    """Stands in for OpenAICompatLLM: .model_id + .chat(messages) -> Reply; reply_fn(prompt, n) → text."""

    model_id = "fake-model"

    def __init__(self, reply_fn=None):
        self.calls = 0
        self.reply_fn = reply_fn or (lambda prompt, n: json.dumps(
            {"name_th": f"หัวข้อ {n}", "name_en": f"Topic {n}", "description": "d", "keywords": ["a", "b"]},
            ensure_ascii=False))

    def chat(self, messages):
        self.calls += 1
        return Reply(self.reply_fn(messages[0]["content"], self.calls), 0, 0, 0.0)


VALID = json.dumps({"name_th": "ข้าวไทย", "name_en": "Thai rice", "description": "d", "keywords": ["ข้าว", "rice"]},
                   ensure_ascii=False)


def _workdir(cfg, titles_by_topic):
    work = cfg["pipeline"]["work_dir"]
    rows, labels = [], []
    for t, titles in titles_by_topic.items():
        for title in titles:
            rows.append({"article_id": f"a{len(rows)}", "title": title, "doc_text": title})
            labels.append(t)
    labels = np.array(labels)
    rng = np.random.default_rng(0)
    emb = rng.normal(size=(len(rows), 8)).astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    ids = sorted(titles_by_topic)
    C = np.stack([emb[labels == t].mean(0) for t in ids])
    C /= np.linalg.norm(C, axis=1, keepdims=True)
    write_table(pd.DataFrame(rows), f"{work}/02_docs.parquet")
    write_table(pd.DataFrame({"article_id": [r["article_id"] for r in rows], "fine_topic": labels}),
                f"{work}/04_fine_topics.parquet")
    write_table(pd.DataFrame({"level": "fine", "topic_id": ids, "size": [len(titles_by_topic[t]) for t in ids],
                              "top_terms": "ข้าว; rice", "top_keywords": "ข้าว; rice", "coarse_topic": 0,
                              "coherence": 0.9}), f"{work}/04_topic_info.parquet")
    np.save(f"{work}/03_embeddings.npy", emb)
    np.save(f"{work}/04_centroids.npy", C)
    open(f"{work}/04_centroid_ids.json", "w", encoding="utf-8").write(json.dumps(ids))


def _llm_cfg(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["labeling"]["provider"] = "llm"
    cfg["pipeline"]["release"] = "2026Q4"
    return cfg


def _meta(cfg):
    return json.loads((Path(cfg["pipeline"]["work_dir"]) / "05_labels_meta.json").read_text(encoding="utf-8"))


def test_representative_indices_central_then_diverse():
    c = np.array([1.0, 0.0, 0.0])
    m = np.array([[1, 0, 0], [0.999, 0.045, 0], [0.9, 0, 0.436]], dtype=np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True)
    # λ=0.3 favours diversity: the near-duplicate of the first pick (row 1) loses to row 2
    assert representative_indices(m, c, 2, lam=0.3) == [0, 2]


def test_fallback_labels_use_author_keywords(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    _workdir(cfg, {1: ["ก", "ข"]})
    info = read_table(f"{cfg['pipeline']['work_dir']}/04_topic_info.parquet")
    info["top_keywords"] = "ผู้สูงอายุ; การดูแลระยะยาว; older adults"
    write_table(info, f"{cfg['pipeline']['work_dir']}/04_topic_info.parquet")
    out = label(cfg)
    assert out.loc[0, "name_th"] == "ผู้สูงอายุ / การดูแลระยะยาว"
    assert out.loc[0, "name_en"] == "older adults" and out.loc[0, "label_source"] == "keywords"


def test_prompt_comes_from_the_prompt_file_with_titles(make_cfg, tmp_path):
    cfg = _llm_cfg(make_cfg, tmp_path)
    _workdir(cfg, {1: ["เรื่องข้าว 1", "เรื่องข้าว 2"]})
    job = label_job(cfg)
    assert job.task == "label" and [it.key for it in job.items] == ["T000001"]
    p = job.items[0].prompt
    assert "- เรื่องข้าว 1" in p and "{titles}" not in p and "c-TF-IDF" in p


def test_llm_labels_cached_by_prompt_content(make_cfg, tmp_path):
    cfg = _llm_cfg(make_cfg, tmp_path)
    _workdir(cfg, {1: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 2: ["เรื่องเบาหวาน 1", "เรื่องเบาหวาน 2"]})
    first = FakeLLM()
    out = label(cfg, llm=first)
    assert first.calls == 2 and (out["label_source"] == "llm").all() and (out["cache_key"] != "fallback").all()
    second = FakeLLM()
    label(cfg, llm=second)
    assert second.calls == 0                                   # nothing changed → all from the LLM cache
    _workdir(cfg, {1: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 2: ["หัวข้อใหม่ทั้งหมด 1", "หัวข้อใหม่ทั้งหมด 2"]})
    third = FakeLLM()
    out = label(cfg, llm=third)
    assert third.calls == 1                                    # only the topic whose members changed
    assert set(out["topic_id"]) == {1, 2} and _meta(cfg)["from_cache"] == 1


def test_invalid_replies_fall_back_and_are_retried_next_run(make_cfg, tmp_path):
    cfg = _llm_cfg(make_cfg, tmp_path)
    _workdir(cfg, {1: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 2: ["เรื่องเบาหวาน 1", "เรื่องเบาหวาน 2"]})
    blank = json.dumps({"name_th": " ", "name_en": "", "description": "d", "keywords": []})
    llm = FakeLLM(lambda p, n: blank if "เบาหวาน" in p else VALID)
    out = label(cfg, llm=llm).set_index("topic_id")
    assert llm.calls == 1 + 3                                  # topic 2: first try + 2 repair turns
    assert out.loc[1, "label_source"] == "llm" and out.loc[2, "cache_key"] == "fallback"
    assert out.loc[2, "label_source"] == "keywords" and out.loc[2, "name_en"] == "rice"
    assert _meta(cfg)["fallback"] == 1
    rerun = FakeLLM(lambda p, n: VALID)
    out = label(cfg, llm=rerun)
    assert rerun.calls == 1 and (out["cache_key"] != "fallback").all()


def test_editor_overrides_win_and_unknown_ids_are_reported(make_cfg, tmp_path):
    cfg = _llm_cfg(make_cfg, tmp_path)
    _workdir(cfg, {1: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 2: ["เรื่องเบาหวาน 1", "เรื่องเบาหวาน 2"]})
    path = tmp_path / "registry" / "label_overrides.csv"
    path.parent.mkdir()
    path.write_text("topic_id,name_th,name_en,description,reviewer,reviewed_at,note\n"
                    "T000002,เบาหวานในผู้สูงอายุ,,,บก. ก,2026-10-01,\nT000099,หายไปแล้ว,Gone,,,,\n",
                    encoding="utf-8-sig")                     # Excel saves CSV with a BOM
    cfg["labeling"]["overrides_path"] = str(path)
    assert load_overrides(path)["topic_id"].tolist() == [2, 99]
    out = label(cfg, llm=FakeLLM(lambda p, n: VALID)).set_index("topic_id")
    assert out.loc[2, "name_th"] == "เบาหวานในผู้สูงอายุ" and out.loc[2, "name_en"] == "Thai rice"
    assert out.loc[2, "label_source"] == "override" and out.loc[1, "label_source"] == "llm"
    meta = _meta(cfg)
    assert meta["overrides"] == 1 and meta["unknown_overrides"] == ["T000099"]
    cfg["labeling"]["provider"] = "off"                        # overrides apply without an LLM too
    assert label(cfg).set_index("topic_id").loc[2, "name_th"] == "เบาหวานในผู้สูงอายุ"


def test_yaml_provider_aliases(tmp_path):
    from atlas.config import load_config

    p = tmp_path / "c.yaml"
    p.write_text("labeling:\n  provider: off\n", encoding="utf-8")       # bare off = YAML false
    assert load_config(p)["labeling"]["provider"] == "off"
    p.write_text("labeling:\n  provider: api\n  overrides_path: registry/o.csv\n", encoding="utf-8")  # P0 name
    cfg = load_config(p)
    assert cfg["labeling"]["provider"] == "llm"
    assert Path(cfg["labeling"]["overrides_path"]) == (tmp_path / "registry" / "o.csv").resolve()
    assert load_config(None)["labeling"]["overrides_path"] is None    # tests never read a real overrides file
