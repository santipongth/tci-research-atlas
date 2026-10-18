import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.label import label, representative_indices


class _Resp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.calls += 1
        return _Resp(json.dumps({"name_th": f"หัวข้อ {self.calls}", "name_en": f"Topic {self.calls}",
                                 "description": "d", "keywords": ["a", "b"]}))


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


def test_representative_indices_central_then_diverse():
    c = np.array([1.0, 0.0, 0.0])
    m = np.array([[1, 0, 0], [0.999, 0.045, 0], [0.9, 0, 0.436]], dtype=np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True)
    # λ=0.3 favours diversity: the near-duplicate of the first pick (row 1) loses to row 2
    assert representative_indices(m, c, 2, lam=0.3) == [0, 2]


def test_fallback_labels_use_author_keywords(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    _workdir(cfg, {0: ["ก", "ข"]})
    info = read_table(f"{cfg['pipeline']['work_dir']}/04_topic_info.parquet")
    info["top_keywords"] = "ผู้สูงอายุ; การดูแลระยะยาว; older adults"
    write_table(info, f"{cfg['pipeline']['work_dir']}/04_topic_info.parquet")
    out = label(cfg)
    assert out.loc[0, "name_th"] == "ผู้สูงอายุ / การดูแลระยะยาว"
    assert out.loc[0, "name_en"] == "older adults"


def test_llm_labels_cached_by_prompt_content(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["labeling"]["provider"] = "api"
    _workdir(cfg, {0: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 1: ["เรื่องเบาหวาน 1", "เรื่องเบาหวาน 2"]})
    first = FakeClient()
    label(cfg, client=first)
    assert first.calls == 2
    second = FakeClient()
    label(cfg, client=second)
    assert second.calls == 0                                   # nothing changed → all from cache
    _workdir(cfg, {0: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 1: ["หัวข้อใหม่ทั้งหมด 1", "หัวข้อใหม่ทั้งหมด 2"]})
    third = FakeClient()
    out = label(cfg, client=third)
    assert third.calls == 1                                    # only the topic whose members changed
    assert len(out) == 2 and set(out["topic_id"]) == {0, 1}


class ScriptedClient:
    """Fake OpenAI-compatible client: content_fn(prompt) returns the raw message text or raises."""

    def __init__(self, content_fn):
        self.calls = 0
        self.content_fn = content_fn
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.calls += 1
        prompt = kwargs["messages"][0]["content"]
        return _Resp(self.content_fn(prompt))


VALID = json.dumps({"name_th": "ข้าวไทย", "name_en": "Thai rice",
                    "description": "d", "keywords": ["ข้าว", "rice"]}, ensure_ascii=False)


def test_fenced_json_with_preamble_is_parsed(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["labeling"]["provider"] = "api"
    cfg["labeling"]["api"]["max_retries"] = 1
    _workdir(cfg, {0: ["เรื่องข้าว 1", "เรื่องข้าว 2"]})
    client = ScriptedClient(lambda p: "Here is the label:\n```json\n" + VALID + "\n```")
    out = label(cfg, client=client)
    assert out.loc[0, "name_th"] == "ข้าวไทย"
    assert out.loc[0, "name_en"] == "Thai rice"
    assert out.loc[0, "cache_key"] != "fallback"


def test_partial_failure_keeps_successes_and_falls_back(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["labeling"]["provider"] = "api"
    cfg["labeling"]["api"]["max_retries"] = 1
    _workdir(cfg, {0: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 1: ["เรื่องเบาหวาน 1", "เรื่องเบาหวาน 2"]})

    def fail_topic1(prompt):
        if "เรื่องเบาหวาน" in prompt:
            raise RuntimeError("boom")
        return VALID

    out = label(cfg, client=ScriptedClient(fail_topic1))
    assert len(out) == 2 and set(out["topic_id"]) == {0, 1}
    assert out.set_index("topic_id").loc[0, "cache_key"] != "fallback"
    assert out.set_index("topic_id").loc[1, "cache_key"] == "fallback"
    assert out.set_index("topic_id").loc[1, "name_en"] == "rice"
    cache = read_table(Path(cfg["pipeline"]["state_dir"]) / "label_cache.parquet")
    assert len(cache) == 1                                     # only the successful topic is cached
    rerun = ScriptedClient(lambda p: VALID)
    out2 = label(cfg, client=rerun)
    assert rerun.calls == 1                                    # only the failed topic is retried
    assert (out2["cache_key"] != "fallback").all()


def test_blank_labels_are_not_cached(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["labeling"]["provider"] = "api"
    cfg["labeling"]["api"]["max_retries"] = 1
    _workdir(cfg, {0: ["เรื่องข้าว 1", "เรื่องข้าว 2"]})
    blank = json.dumps({"name_th": "", "name_en": "", "description": "d", "keywords": []})
    client = ScriptedClient(lambda p: blank)
    out = label(cfg, client=client)
    assert client.calls == 1
    assert out.loc[0, "cache_key"] == "fallback"
    assert not (Path(cfg["pipeline"]["state_dir"]) / "label_cache.parquet").exists()
