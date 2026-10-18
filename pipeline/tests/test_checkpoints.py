import json

import numpy as np
import pandas as pd
import pytest

from atlas.checkpoints import CheckpointMismatch, docs_fingerprint, load_aligned
from atlas.cluster import cluster
from atlas.embed import embed
from atlas.io_utils import read_table, write_table


def _docs(work, n=12):
    texts = [f"การศึกษาเรื่องที่ {i} about rice farming {i % 3}" for i in range(n)]
    write_table(pd.DataFrame({"article_id": [f"a{i}" for i in range(n)], "doc_text": texts}), work / "02_docs.parquet")


def test_embed_records_a_fingerprint_that_load_aligned_checks(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["embedding"]["provider"] = "lite"                       # the P0 default became "local"
    cfg["embedding"]["lite"].update(dim=4, min_df=1)
    work = tmp_path / "work"
    _docs(work)
    embed(cfg)
    meta = json.loads((work / "03_meta.json").read_text(encoding="utf-8"))
    assert meta["docs_fingerprint"] == docs_fingerprint([f"a{i}" for i in range(12)])
    df, emb = load_aligned(work)
    assert len(df) == len(emb) == 12
    write_table(read_table(work / "02_docs.parquet").iloc[::-1], work / "02_docs.parquet")   # same rows, new order
    with pytest.raises(CheckpointMismatch, match="different 02_docs"):
        load_aligned(work)


def test_row_count_mismatch_stops_the_cluster_step(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = tmp_path / "work"
    _docs(work, n=12)
    np.save(work / "03_embeddings.npy", np.zeros((11, 4), dtype=np.float32))
    with pytest.raises(CheckpointMismatch, match="re-run the embed step"):
        cluster(cfg)
