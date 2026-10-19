"""Step `sdg` (after institutions): research topics → the SDGs and Thai frameworks (BCG, แผนด้าน ววน. 2566–2570,
หมุดหมายแผนพัฒนาฯ ฉบับที่ 13) → work/16_* (export publishes sdg.json and Topic.sdg).

Goals and keywords are curated in atlas/data/frameworks.yaml (sdg.frameworks_path replaces it). Each topic keeps at
most sdg.max_goals_per_topic goals per framework, scored by
  embedding  cosine of the topic centroid (04_centroids.npy) and the embedded goal text "th en: keywords" — used for
             sdg.method embedding, or auto with an api/local embedding provider and centroids on disk; ≥ min_similarity
  lexical    otherwise (or when embedding fails): the share of the topic's articles (≤ sdg.docs_per_topic, seeded
             sample) whose title or keywords name a goal keyword (text folded like the web search; Latin keywords as
             whole words); ≥ sdg.min_article_share
  16_topic_goals    topic_id, framework, goal_id, score
  16_sdg_meta.json  method, version (yaml version + sha1), frameworks [{key, th, en, goals [{id, number, th, en}]}]
A machine-made overview, not an official classification (the web says so). Abstracts are not read.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from atlas.embed import embed_texts
from atlas.io_utils import read_table, write_table
from atlas.matcher import match_fold

FRAMEWORKS_YAML = Path(__file__).parent / "data" / "frameworks.yaml"
TEXT_COLUMNS = ("title", "title_th", "title_en", "keywords_th", "keywords_en")
GOAL_COLUMNS = ["topic_id", "framework", "goal_id", "score"]
GOAL_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")


class FrameworkError(ValueError):
    """frameworks.yaml cannot be used — the message names the goal."""


def load_frameworks(path: str | Path | None = None) -> dict:
    p = Path(path) if path else FRAMEWORKS_YAML
    raw = p.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    seen: set[str] = set()
    for fw in data.get("frameworks") or []:
        if not fw.get("key") or not fw.get("th") or not fw.get("en"):
            raise FrameworkError(f"{p}: every framework needs key, th and en")
        for g in fw.get("goals") or []:
            gid = str(g.get("id", ""))
            if not GOAL_ID.fullmatch(gid) or gid in seen:
                raise FrameworkError(f"{p}: goal id {gid!r} is missing, malformed or repeated")
            seen.add(gid)
            if not isinstance(g.get("number"), int) or not g.get("th") or not g.get("en"):
                raise FrameworkError(f"{p}: goal {gid} needs number, th and en")
            kws = g.get("keywords") or []
            if not kws or not all(isinstance(k, str) and k.strip() for k in kws):
                raise FrameworkError(f"{p}: goal {gid} needs a non-empty list of keywords")
    if not seen:
        raise FrameworkError(f"{p}: no goals")
    data["sha1"] = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return data


def goal_patterns(goals: list[dict]) -> dict[str, re.Pattern]:
    out = {}
    for g in goals:
        parts = []
        for kw in g["keywords"]:
            f = match_fold(kw)
            if f:
                parts.append(rf"(?<![a-z0-9]){re.escape(f)}(?![a-z0-9])" if re.search("[a-z0-9]", f) else re.escape(f))
        out[g["id"]] = re.compile("|".join(sorted(parts, key=len, reverse=True)))
    return out


def lexical_scores(texts: pd.DataFrame, patterns: dict[str, re.Pattern]) -> pd.DataFrame:
    """texts: topic_id, text (folded) → topic_id, goal_id, score (share of the topic's texts naming the goal)."""
    n = texts.groupby("topic_id").size()
    rows = []
    for gid, rx in patterns.items():
        hit = texts["text"].map(lambda s, rx=rx: rx.search(s) is not None).astype(int)
        share = hit.groupby(texts["topic_id"]).sum() / n
        rows += [{"topic_id": int(t), "goal_id": gid, "score": float(v)} for t, v in share.items() if v > 0]
    return pd.DataFrame(rows, columns=["topic_id", "goal_id", "score"])


def similarity_scores(C: np.ndarray, topic_ids: list[int], G: np.ndarray, goal_ids: list[str]) -> pd.DataFrame:
    unit = lambda m: m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-12)  # noqa: E731
    sim = unit(np.asarray(C, dtype=float)) @ unit(np.asarray(G, dtype=float)).T
    return pd.DataFrame([{"topic_id": int(t), "goal_id": g, "score": float(sim[i, j])}
                         for i, t in enumerate(topic_ids) for j, g in enumerate(goal_ids)],
                        columns=["topic_id", "goal_id", "score"])


def pick(scores: pd.DataFrame, goal_framework: dict[str, str], threshold: float, k: int) -> pd.DataFrame:
    s = scores[scores["score"] >= threshold].assign(framework=lambda d: d["goal_id"].map(goal_framework))
    s = s.sort_values(["topic_id", "framework", "score", "goal_id"], ascending=[True, True, False, True])
    return s.groupby(["topic_id", "framework"]).head(k)[GOAL_COLUMNS].reset_index(drop=True)


def _topic_texts(work: Path, per_topic: int, seed: int) -> pd.DataFrame:
    docs = read_table(work / "02_docs.parquet")
    cols = [c for c in TEXT_COLUMNS if c in docs.columns]
    fine = read_table(work / "04_fine_topics.parquet")[["article_id", "fine_topic"]]
    d = docs[["article_id", *cols]].merge(fine, on="article_id")
    d = d[d["fine_topic"].fillna(-1).astype(int) >= 0]
    d = d.sample(frac=1.0, random_state=seed).groupby("fine_topic").head(per_topic)
    text = d[cols].fillna("").astype(str).agg(" ".join, axis=1).map(match_fold)
    return pd.DataFrame({"topic_id": d["fine_topic"].astype(int).to_numpy(), "text": text.to_numpy()})


def _goal_text(g: dict) -> str:
    return f"{g['th']} {g['en']}: " + ", ".join(g["keywords"])


def sdg(cfg: dict, embedder=None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    scfg = cfg["sdg"]
    for stale in work.glob("16_*"):
        stale.unlink()
    if not scfg["enabled"]:
        print("[sdg] sdg.enabled is false — no SDG module")
        return pd.DataFrame(columns=GOAL_COLUMNS)
    fw = load_frameworks(scfg["frameworks_path"])
    goals = [dict(g, framework=f["key"]) for f in fw["frameworks"] for g in f["goals"]]
    goal_framework = {g["id"]: g["framework"] for g in goals}
    method = scfg["method"]
    centroids = work / "04_centroids.npy"
    if method == "auto":
        method = "embedding" if cfg["embedding"]["provider"] in ("api", "local") and centroids.exists() else "lexical"
    scores, threshold = None, 0.0
    if method == "embedding":
        try:
            ids = [int(t) for t in json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))]
            G = embed_texts(cfg, [_goal_text(g) for g in goals], embedder)
            scores = similarity_scores(np.load(centroids), ids, G, [g["id"] for g in goals])
            threshold = float(scfg["min_similarity"])
        except (FileNotFoundError, ImportError, OSError, ValueError, RuntimeError) as e:
            print(f"[sdg] WARNING: embedding mapping unavailable ({type(e).__name__}: {e}) — lexical mapping instead")
            method = "lexical"
    if method == "lexical":
        texts = _topic_texts(work, int(scfg["docs_per_topic"]), int(cfg["pipeline"]["seed"]))
        scores, threshold = lexical_scores(texts, goal_patterns(goals)), float(scfg["min_article_share"])
    out = pick(scores, goal_framework, threshold, int(scfg["max_goals_per_topic"]))
    write_table(out, work / "16_topic_goals.parquet")
    meta = {"method": method, "version": f"{fw.get('version', 1)}-{fw['sha1']}",
            "frameworks": [{"key": f["key"], "th": f["th"], "en": f["en"],
                            "goals": [{"id": g["id"], "number": int(g["number"]), "th": g["th"], "en": g["en"]}
                                      for g in f["goals"]]} for f in fw["frameworks"]]}
    (work / "16_sdg_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[sdg] {method}: {out['topic_id'].nunique():,} topics matched to {out['goal_id'].nunique():,} goals")
    return out
