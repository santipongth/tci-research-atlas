"""Taxonomy anchoring: every fine topic → an OpenAlex subfield (→ field = its group on the map).

Reference set: works with Thai-affiliated authors from OpenAlex (atlas.openalex), embedded with the
SAME embedding model as the corpus (api/local: through the persistent store; lite: fitted jointly on
corpus + reference texts, because lite vectors only exist per fit). For each topic, its articles
closest to the centroid (≤ max_articles_per_topic) each take the similarity-weighted vote of their k
nearest reference works; the topic's subfield is the plurality of those article votes, vote_share is
the plurality's share and cross_field = vote_share < min_vote_share. Groups = OpenAlex fields.
Held-out accuracy of the same kNN rule on the reference set itself is recorded as a quality number.

Never hard-fails: taxonomy.source=off, offline, API errors or an empty reference set fall back to the
P0 agglomerative groups (04_topic_info.coarse_topic) with source="agglomerative".
Outputs: work/10_taxonomy, work/10_taxonomy_meta.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.checkpoints import load_aligned
from atlas.embed import embed_texts, lite_embed
from atlas.io_utils import read_table, write_table
from atlas.openalex import Fetch, OpenAlexUnavailable, load_reference

TAXONOMY_COLUMNS = ["topic_id", "group_id", "group_en", "group_th", "subfield_id", "subfield_en",
                    "vote_share", "cross_field", "source"]
# OpenAlex's 26 fields (ids = Scopus ASJC two-digit codes) with Thai names for the map legend
FIELD_TH = {
    "11": "เกษตรศาสตร์และชีววิทยา", "12": "ศิลปศาสตร์และมนุษยศาสตร์", "13": "ชีวเคมี พันธุศาสตร์ และอณูชีววิทยา",
    "14": "ธุรกิจ การจัดการ และการบัญชี", "15": "วิศวกรรมเคมี", "16": "เคมี", "17": "วิทยาการคอมพิวเตอร์",
    "18": "วิทยาการตัดสินใจ", "19": "วิทยาศาสตร์โลกและดาวเคราะห์", "20": "เศรษฐศาสตร์ เศรษฐมิติ และการเงิน",
    "21": "พลังงาน", "22": "วิศวกรรมศาสตร์", "23": "วิทยาศาสตร์สิ่งแวดล้อม", "24": "ภูมิคุ้มกันวิทยาและจุลชีววิทยา",
    "25": "วัสดุศาสตร์", "26": "คณิตศาสตร์", "27": "แพทยศาสตร์", "28": "ประสาทวิทยาศาสตร์", "29": "พยาบาลศาสตร์",
    "30": "เภสัชวิทยา พิษวิทยา และเภสัชศาสตร์", "31": "ฟิสิกส์และดาราศาสตร์", "32": "จิตวิทยา", "33": "สังคมศาสตร์",
    "34": "สัตวแพทยศาสตร์", "35": "ทันตแพทยศาสตร์", "36": "วิชาชีพด้านสุขภาพ",
}


def knn_vote(query: np.ndarray, ref: np.ndarray, ref_labels: np.ndarray, k: int,
             chunk: int = 1024) -> tuple[np.ndarray, np.ndarray]:
    """Similarity-weighted kNN vote → (label per query row, winning weight share). Rows are unit vectors."""
    k = max(1, min(k, len(ref)))
    classes, codes = np.unique(ref_labels, return_inverse=True)
    pred = np.empty(len(query), dtype=classes.dtype)
    conf = np.empty(len(query))
    for s in range(0, len(query), chunk):
        sim = query[s:s + chunk] @ ref.T
        idx = np.argpartition(-sim, k - 1, axis=1)[:, :k]
        w = np.maximum(np.take_along_axis(sim, idx, axis=1), 0.0) + 1e-6
        votes = np.zeros((len(idx), len(classes)))
        np.add.at(votes, (np.repeat(np.arange(len(idx)), k), codes[idx].ravel()), w.ravel())
        best = votes.argmax(axis=1)
        pred[s:s + chunk] = classes[best]
        conf[s:s + chunk] = votes[np.arange(len(idx)), best] / votes.sum(axis=1)
    return pred, conf


def holdout_accuracy(ref_emb: np.ndarray, labels: np.ndarray, k: int, frac: float, seed: int) -> float | None:
    """kNN accuracy on a random held-out part of the reference set (None when a side would be empty)."""
    rng = np.random.default_rng(seed)
    test = rng.random(len(labels)) < frac
    if test.sum() == 0 or (~test).sum() == 0:
        return None
    pred, _ = knn_vote(ref_emb[test], ref_emb[~test], labels[~test], k)
    return round(float((pred == labels[test]).mean()), 4)


def topic_votes(labels: np.ndarray, emb: np.ndarray, ids: list[int], C: np.ndarray, ref_emb: np.ndarray,
                ref_sub: np.ndarray, k: int, max_articles: int) -> pd.DataFrame:
    rows = []
    for i, tid in enumerate(ids):
        members = np.where(labels == tid)[0]
        if len(members) > max_articles:
            members = members[np.argsort(-(emb[members] @ C[i]), kind="stable")[:max_articles]]
        pred, _ = knn_vote(emb[members], ref_emb, ref_sub, k)
        vc = pd.Series(pred).value_counts()
        top = vc[vc == vc.iloc[0]].index
        winner = sorted(str(t) for t in top)[0]                 # deterministic tie-break
        rows.append({"topic_id": tid, "subfield_id": winner, "vote_share": float(vc.iloc[0] / len(pred)),
                     "n_voted": int(len(pred))})
    return pd.DataFrame(rows)


def load_topic_groups(work: str | Path) -> pd.DataFrame:
    """topic_id, group_id (int), group_en, group_th — from 10_taxonomy, else the P0 coarse groups."""
    work = Path(work)
    try:
        t = read_table(work / "10_taxonomy.parquet")
        return t[["topic_id", "group_id", "group_en", "group_th"]].astype({"group_id": int})
    except FileNotFoundError:
        info = read_table(work / "04_topic_info.parquet")
        return pd.DataFrame({"topic_id": info["topic_id"], "group_id": info["coarse_topic"].astype(int),
                             "group_en": "", "group_th": ""})


def _fallback(info: pd.DataFrame, reason: str) -> tuple[pd.DataFrame, dict]:
    out = pd.DataFrame({"topic_id": info["topic_id"], "group_id": info["coarse_topic"].astype(int),
                        "group_en": "", "group_th": "", "subfield_id": "", "subfield_en": "",
                        "vote_share": np.nan, "cross_field": False, "source": "agglomerative"},
                       columns=TAXONOMY_COLUMNS)
    return out, {"source": "agglomerative", "version": None, "reason": reason}


def taxonomy(cfg: dict, fetch: Fetch | None = None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    tcfg, seed = cfg["taxonomy"], int(cfg["pipeline"]["seed"])
    info = read_table(work / "04_topic_info.parquet")
    try:
        if tcfg["source"] == "off":
            raise OpenAlexUnavailable("taxonomy.source is off")
        ref, ref_meta = load_reference(cfg, fetch)
        if ref.empty:
            raise OpenAlexUnavailable("empty reference set")
    except (OpenAlexUnavailable, OSError, ValueError) as e:
        out, meta = _fallback(info, str(e))
        print(f"[taxonomy] WARNING: OpenAlex taxonomy unavailable ({e}) → agglomerative groups")
    else:
        docs, emb = load_aligned(work)
        ref_text = (ref["title"].fillna("") + " . " + ref["abstract"].fillna("")).str.slice(
            0, int(cfg["embedding"]["max_chars_per_doc"])).tolist()
        if cfg["embedding"]["provider"] == "lite":
            joint = lite_embed(docs["doc_text"].tolist() + ref_text, cfg["embedding"]["lite"], seed)
            joint /= np.maximum(np.linalg.norm(joint, axis=1, keepdims=True), 1e-9)
            emb, ref_emb = joint[:len(docs)], joint[len(docs):]
        else:
            ref_emb = embed_texts(cfg, ref_text)
        labels = (docs[["article_id"]].merge(read_table(work / "04_fine_topics.parquet"), on="article_id",
                                             how="left")["fine_topic"].fillna(-1).astype(int).to_numpy())
        ids = [int(t) for t in json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))]
        C = np.stack([emb[labels == t].mean(axis=0) for t in ids]) if ids else np.zeros((0, emb.shape[1]))
        C /= np.maximum(np.linalg.norm(C, axis=1, keepdims=True), 1e-9)
        sub = ref["subfield_id"].astype(str).to_numpy()
        votes = topic_votes(labels, emb, ids, C, ref_emb, sub, int(tcfg["k"]), int(tcfg["max_articles_per_topic"]))
        names = ref.drop_duplicates("subfield_id").set_index("subfield_id")
        out = votes.assign(
            subfield_en=votes["subfield_id"].map(names["subfield_en"]),
            group_id=votes["subfield_id"].map(names["field_id"]).astype(int),
            group_en=votes["subfield_id"].map(names["field_en"]),
            cross_field=votes["vote_share"] < float(tcfg["min_vote_share"]),
            source="openalex")
        out["group_th"] = out["group_id"].astype(str).map(FIELD_TH).fillna(out["group_en"])
        out = out[TAXONOMY_COLUMNS]
        k, frac = int(tcfg["k"]), float(tcfg["holdout_frac"])
        meta = {"source": "openalex", "version": ref_meta["version"], "reference_origin": ref_meta["origin"],
                "n_reference": int(len(ref)), "k": k,
                "holdout_accuracy_subfield": holdout_accuracy(ref_emb, sub, k, frac, seed),
                "holdout_accuracy_field": holdout_accuracy(ref_emb, ref["field_id"].astype(str).to_numpy(), k,
                                                           frac, seed),
                "n_cross_field": int(out["cross_field"].sum())}
        print(f"[taxonomy] {len(out)} topics → {out['group_id'].nunique()} OpenAlex fields "
              f"({meta['n_cross_field']} cross-field); held-out subfield accuracy "
              f"{meta['holdout_accuracy_subfield']} on {len(ref):,} reference works")
    write_table(out, work / "10_taxonomy.parquet")
    (work / "10_taxonomy_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return out
