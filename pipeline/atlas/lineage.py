"""Stable topic IDs across releases + lineage events.

Topic ids are stable integers N, published as "T%06d" (T000123). A release either
  assigns  — keeps last release's topics; articles seen before keep their topic, new
             articles join the nearest topic centroid (cosine ≥ outlier_min_similarity)
  fits     — clusters from scratch, then matches new clusters to last release's topics
             through the articles they share.

Matching (fit): M[o, n] = articles shared by old topic o and new cluster n.
  c_old = M / |o ∩ current docs|   (how much of o went into n)
  c_new = M / |n ∩ previous docs|  (how much of n came from o)
  edge o–n  ⇔  M ≥ match_min_shared and (c_old ≥ θ or c_new ≥ θ), θ = match_containment
Inside each connected component, pairs are taken greedily by (shared articles, centroid
cosine, smaller old id) so each old id is inherited at most once. Events per new topic:
  merge (≥ 2 old sources) · split (its source has ≥ 2 heirs) · continue · new (no edge);
old topics with no edge are retired. Centroid cosine is computed in the CURRENT embedding
space (old topic = mean of its articles' current vectors), so it works even when the
embedding space changes between runs (lite provider).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.state import release_dir

EVENTS = ("new", "continue", "split", "merge", "retired")
EVENT_COLUMNS = ["event", "topic_id", "parents"]


def topic_code(tid: int) -> str:
    return f"T{int(tid):06d}"


def _unit(v: np.ndarray) -> np.ndarray:
    return v / max(float(np.linalg.norm(v)), 1e-9)


def member_centroids(article_ids: pd.Series, emb: np.ndarray, assignments: pd.DataFrame) -> dict[int, np.ndarray]:
    """Unit centroid (current space) of every topic in `assignments` from its articles present now."""
    pos = pd.Series(np.arange(len(article_ids)), index=article_ids.to_numpy())
    a = assignments[(assignments["topic_id"] >= 0) & assignments["article_id"].isin(pos.index)]
    out: dict[int, np.ndarray] = {}
    for tid, g in a.groupby("topic_id"):
        out[int(tid)] = _unit(emb[pos.loc[g["article_id"]].to_numpy()].mean(axis=0))
    return out


def match_topics(prev: pd.DataFrame, cur: pd.DataFrame, old_vec: dict[int, np.ndarray],
                 new_vec: dict[int, np.ndarray], next_id: int, containment: float,
                 min_shared: int) -> tuple[dict[int, int], pd.DataFrame, int]:
    """prev: article_id, topic_id (stable, last release) · cur: article_id, topic_id (temporary, this fit).

    Returns ({temporary id → stable id}, events [event, topic_id, parents], next free id).
    """
    prev = prev[prev["topic_id"] >= 0]
    cur_all = cur
    cur = cur[cur["topic_id"] >= 0]
    new_ids = sorted(int(t) for t in cur["topic_id"].unique())
    old_ids = sorted(int(t) for t in prev["topic_id"].unique())
    shared = prev.merge(cur, on="article_id", suffixes=("_old", "_new"))
    M = shared.groupby(["topic_id_old", "topic_id_new"]).size()
    old_size = prev[prev["article_id"].isin(set(cur_all["article_id"]))].groupby("topic_id").size()
    new_size = cur[cur["article_id"].isin(set(prev["article_id"]))].groupby("topic_id").size()

    edges: dict[tuple[int, int], int] = {}
    for (o, n), m in M.items():
        c_old = m / max(int(old_size.get(o, 0)), 1)
        c_new = m / max(int(new_size.get(n, 0)), 1)
        if m >= min_shared and (c_old >= containment or c_new >= containment):
            edges[(int(o), int(n))] = int(m)
    sources: dict[int, set[int]] = {n: set() for n in new_ids}
    heirs: dict[int, set[int]] = {o: set() for o in old_ids}
    for o, n in edges:
        sources[n].add(o)
        heirs[o].add(n)

    def cos(o: int, n: int) -> float:
        if o in old_vec and n in new_vec:
            return float(old_vec[o] @ new_vec[n])
        return -1.0

    mapping: dict[int, int] = {}
    used: set[int] = set()
    for (o, n), _m in sorted(edges.items(), key=lambda kv: (-kv[1], -cos(*kv[0]), kv[0][0], kv[0][1])):
        if o not in used and n not in mapping:
            mapping[n] = o
            used.add(o)
    rows = []
    for n in new_ids:
        if n not in mapping:
            mapping[n], next_id = next_id, next_id + 1
        src = sorted(sources[n])
        if len(src) >= 2:
            rows.append(("merge", mapping[n], src))
        elif len(src) == 1 and len(heirs[src[0]]) >= 2:
            rows.append(("split", mapping[n], src))
        elif len(src) == 1 and mapping[n] == src[0]:
            rows.append(("continue", mapping[n], []))
        elif len(src) == 1:                  # its source's id went to a larger partner (many-to-many)
            rows.append(("split", mapping[n], src))
        else:
            rows.append(("new", mapping[n], []))
    for o in old_ids:
        if not heirs[o]:
            rows.append(("retired", o, []))
    events = pd.DataFrame([{"event": e, "topic_id": t, "parents": ";".join(map(str, p))} for e, t, p in rows],
                          columns=EVENT_COLUMNS)
    return mapping, events, next_id


def kept_fraction(prev_ids: set[int], cur_ids: set[int]) -> float:
    """Share of last release's topic ids that still exist."""
    return len(prev_ids & cur_ids) / len(prev_ids) if prev_ids else 1.0


def assign_to_previous(article_ids: pd.Series, emb: np.ndarray, prev_assign: pd.DataFrame,
                       min_sim: float) -> tuple[np.ndarray, int, int]:
    """Assign mode. Returns (labels aligned with article_ids, n_new_articles, n_new_unassigned)."""
    known = dict(zip(prev_assign["article_id"], prev_assign["topic_id"].astype(int)))
    labels = np.array([known.get(a, -2) for a in article_ids], dtype=int)      # −2 = never seen
    vecs = member_centroids(article_ids, emb, prev_assign)
    is_new = labels == -2
    todo = np.where(labels < 0)[0]                                            # new + previously unassigned
    if len(todo) and vecs:
        ids = np.array(sorted(vecs))
        C = np.stack([vecs[t] for t in ids])
        sim = emb[todo] @ C.T
        labels[todo] = np.where(sim.max(axis=1) >= min_sim, ids[sim.argmax(axis=1)], -1)
    labels[labels == -2] = -1
    return labels, int(is_new.sum()), int((is_new & (labels < 0)).sum())


# ------------------------------------------------------------------ persistent state
def _topics_dir(cfg: dict, release: str) -> Path:
    return release_dir(cfg, release) / "topics"


def load_topic_state(cfg: dict, release: str | None) -> dict | None:
    """{"assignments", "registry", "model"} of a release, or None when it has no topic state."""
    if not release:
        return None
    d = _topics_dir(cfg, release)
    if not (d / "model.json").exists():
        return None
    return {"assignments": read_table(d / "assignments.parquet"),
            "registry": read_table(d / "registry.parquet"),
            "model": json.loads((d / "model.json").read_text(encoding="utf-8"))}


def save_topic_state(cfg: dict, release: str, assignments: pd.DataFrame, registry: pd.DataFrame,
                     events: pd.DataFrame, model: dict) -> Path:
    release_dir(cfg, release, create=True)
    d = _topics_dir(cfg, release)
    d.mkdir(parents=True, exist_ok=True)
    write_table(assignments.reset_index(drop=True), d / "assignments.parquet")
    write_table(registry.reset_index(drop=True), d / "registry.parquet")
    write_table(events.reset_index(drop=True), d / "lineage.parquet")
    (d / "model.json").write_text(json.dumps(model, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def update_registry(prev_registry: pd.DataFrame | None, active_ids: list[int], events: pd.DataFrame,
                    release: str) -> pd.DataFrame:
    """topic_id, born, status (active | retired | merged), last_seen — one row per id ever issued."""
    cols = ["topic_id", "born", "status", "last_seen"]
    reg = prev_registry.copy() if prev_registry is not None else pd.DataFrame(columns=cols)
    reg = reg.set_index("topic_id") if len(reg) else pd.DataFrame(columns=cols[1:])
    merged_away = {int(p) for ps in events.loc[events["event"] == "merge", "parents"] for p in str(ps).split(";") if p}
    for tid in reg.index:
        if int(tid) not in active_ids and reg.loc[tid, "status"] == "active":
            reg.loc[tid, "status"] = "merged" if int(tid) in merged_away else "retired"
    for tid in active_ids:
        born = reg.loc[tid, "born"] if tid in reg.index else release
        reg.loc[tid, ["born", "status", "last_seen"]] = [born, "active", release]
    out = reg.reset_index().rename(columns={"index": "topic_id"})
    out["topic_id"] = out["topic_id"].astype(int)
    return out[cols].sort_values("topic_id").reset_index(drop=True)
