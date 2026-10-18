import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from atlas.embed import embed, lite_embed
from atlas.embed_store import EmbeddingStore, text_key
from atlas.io_utils import write_table
from atlas.preprocess import build_doc_texts


class FakeEmbedder:
    model_id = "fake|1"

    def __init__(self, fail_on_call: int | None = None):
        self.calls, self.fail_on_call = 0, fail_on_call

    def embed_batch(self, texts):
        self.calls += 1
        if self.fail_on_call and self.calls == self.fail_on_call:
            raise RuntimeError("simulated crash")
        return np.stack([np.frombuffer(hashlib.sha256(t.encode()).digest()[:16], dtype=np.uint8)
                         .astype(np.float32) + 1 for t in texts])


def _norm(a):
    return a / np.linalg.norm(a, axis=1, keepdims=True)


def test_build_doc_texts_joins_non_empty_fields():
    df = pd.DataFrame({"a": ["x", ""], "b": ["y", "z"]})
    assert build_doc_texts(df, ["a", "b", "missing"], 100) == ["x . y", "z"]
    assert build_doc_texts(df, ["a", "b"], 3) == ["x .", "z"]


def test_store_roundtrip_and_resume(tmp_path):
    a = np.arange(6, dtype=np.float32).reshape(2, 3)
    s = EmbeddingStore(tmp_path, "m")
    s.add(["k1", "k2"], a)
    s2 = EmbeddingStore(tmp_path, "m")                     # a new process sees what was flushed
    assert len(s2) == 2 and s2.has("k1")
    s2.add(["k2", "k3"], np.array([[9, 9, 9], [7, 7, 7]], dtype=np.float32))   # k2 already stored
    got = s2.get(["k3", "k1", "k2"])
    assert np.array_equal(got, np.array([[7, 7, 7], [0, 1, 2], [3, 4, 5]], dtype=np.float32))
    with pytest.raises(KeyError):
        s2.get(["nope"])


def test_store_keys_depend_on_model():
    assert text_key("m1", "t") != text_key("m2", "t")


def test_lite_embed_is_deterministic():
    texts = [f"การศึกษาเรื่องที่ {i} about topic {i % 3}" for i in range(40)]
    cfg = {"dim": 8, "ngram_min": 2, "ngram_max": 4, "max_features": 5000, "min_df": 1}
    a, b = lite_embed(texts, cfg, 42), lite_embed(texts, cfg, 42)
    assert a.shape == (40, 8) and np.allclose(a, b)


def _docs(make_cfg, tmp_path, n=10):
    cfg = make_cfg(tmp_path)
    cfg["embedding"]["provider"] = "api"
    cfg["embedding"]["api"].update(batch_size=2, checkpoint_every=2)
    texts = [f"เอกสารทดสอบหมายเลข {i} for embedding" for i in range(n)]
    write_table(pd.DataFrame({"article_id": [f"a{i}" for i in range(n)], "doc_text": texts}),
                f"{cfg['pipeline']['work_dir']}/02_docs.parquet")
    return cfg, texts


def test_embed_resumes_after_interruption(make_cfg, tmp_path):
    cfg, texts = _docs(make_cfg, tmp_path)
    with pytest.raises(RuntimeError):
        embed(cfg, embedder=FakeEmbedder(fail_on_call=3))        # crashes on the 3rd batch
    fake = FakeEmbedder()
    arr = embed(cfg, embedder=fake)
    assert fake.calls == 3                                        # 10 texts − 4 already stored = 3 batches of 2
    assert np.allclose(arr, _norm(FakeEmbedder().embed_batch(texts)), atol=1e-6)
    meta = json.loads(open(f"{cfg['pipeline']['work_dir']}/03_meta.json", encoding="utf-8").read())
    assert meta == {"model_id": "fake|1", "n": 10, "dim": 16}


def test_embed_second_run_uses_store_only(make_cfg, tmp_path):
    cfg, _ = _docs(make_cfg, tmp_path)
    embed(cfg, embedder=FakeEmbedder())
    again = FakeEmbedder()
    embed(cfg, embedder=again)
    assert again.calls == 0


def test_embed_crash_with_partial_buffer_keeps_paid_vectors(make_cfg, tmp_path):
    cfg, texts = _docs(make_cfg, tmp_path)
    cfg["embedding"]["api"].update(batch_size=2, checkpoint_every=4)
    with pytest.raises(RuntimeError):
        embed(cfg, embedder=FakeEmbedder(fail_on_call=4))   # batches 1-3 succeed, flush at 4 vectors, 2 buffered
    fake = FakeEmbedder()
    embed(cfg, embedder=fake)
    assert fake.calls == 2                                   # 10 texts − 6 kept = 4 → 2 batches
