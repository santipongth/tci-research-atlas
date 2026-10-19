"""Bake-offs — pick the embedding model and the clustering algorithm by numbers, not belief.

Embedding candidates (bakeoff.embedding_candidates) are scored on our own Thai works:
  journal_knn_acc    kNN (k) accuracy of predicting an article's journal from held-out neighbours
  subfield_knn_acc   kNN accuracy of the OpenAlex subfield on held-out Thai reference works (if available)
  truth_purity       mean share of each article's k nearest neighbours with the same planted topic
                     (synthetic corpus only — needs a truth CSV: article_id, topic)
Clustering algorithms (bakeoff.algorithms: hdbscan = UMAP→HDBSCAN→merge with sklearn, hdbscan_fast = the
same with fast_hdbscan, leiden = Leiden on a kNN graph) are run with every seed in bakeoff.seeds on the
same embeddings:
  ari_stability      mean pairwise adjusted Rand index between seeds (1 = identical partitions)
  ari_vs_first       ARI of the first run against the first algorithm's first run (do two backends agree?)
  purity             mean majority-topic share per cluster against the truth (synthetic only)
  npmi               mean NPMI coherence of each cluster's top c-TF-IDF terms over document co-occurrence
API candidates embed through the P0 runner (atlas.embed.embed_texts) into one store per store_id, so a
bake-off sample is paid for once and a winning model's vectors are reused by the real run.
The report is Markdown; nothing here changes the pipeline's configuration.
"""
from __future__ import annotations

import copy
import importlib.util
import itertools
import math
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.ctfidf import topic_terms
from atlas.taxonomy import knn_vote
from atlas.thai import tokenize

EmbedFn = Callable[[list[str]], np.ndarray]


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _unit(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float32)
    return X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)


# ------------------------------------------------------------------ metrics
def knn_accuracy(X: np.ndarray, y, k: int, holdout_frac: float, seed: int) -> float:
    y = np.asarray(y).astype(str)
    test = np.random.default_rng(seed).random(len(y)) < holdout_frac
    if not test.any() or test.all():
        return math.nan
    pred, _ = knn_vote(X[test], X[~test], y[~test], k)
    return float((pred == y[test]).mean())


def neighbor_purity(X: np.ndarray, y, k: int) -> float:
    y = np.asarray(y).astype(str)
    sim = X @ X.T
    np.fill_diagonal(sim, -np.inf)
    k = max(1, min(k, len(y) - 1))
    idx = np.argpartition(-sim, k - 1, axis=1)[:, :k]
    return float((y[idx] == y[:, None]).mean())


def purity(labels: np.ndarray, truth) -> float:
    """Mean over clusters (unassigned −1 excluded) of the majority truth label's share."""
    df = pd.DataFrame({"c": labels, "t": np.asarray(truth)})
    df = df[df["c"] >= 0]
    if df.empty:
        return math.nan
    return float(df.groupby("c")["t"].agg(lambda s: s.value_counts().iloc[0] / len(s)).mean())


def ari_stability(runs: list[np.ndarray]) -> float:
    from sklearn.metrics import adjusted_rand_score

    pairs = list(itertools.combinations(runs, 2))
    return float(np.mean([adjusted_rand_score(a, b) for a, b in pairs])) if pairs else math.nan


def npmi_coherence(top_terms: dict[int, list[str]], doc_tokens: list[set[str]], top_n: int) -> float:
    n = len(doc_tokens)
    if not n:
        return math.nan
    df: dict[str, set[int]] = {}
    wanted = {t for terms in top_terms.values() for t in terms[:top_n]}
    for i, toks in enumerate(doc_tokens):
        for t in toks & wanted:
            df.setdefault(t, set()).add(i)
    scores = []
    for terms in top_terms.values():
        ts = [t for t in terms[:top_n] if t in df]
        vals = []
        for a, b in itertools.combinations(ts, 2):
            joint = len(df[a] & df[b])
            if joint == 0:
                vals.append(-1.0)
                continue
            pj, pa, pb = joint / n, len(df[a]) / n, len(df[b]) / n
            vals.append(1.0 if pj == 1.0 else math.log(pj / (pa * pb)) / -math.log(pj))
        if vals:
            scores.append(float(np.mean(vals)))
    return float(np.mean(scores)) if scores else math.nan


# ------------------------------------------------------------------ embedding bake-off
def embedding_bakeoff(texts: list[str], journals, candidates: dict[str, EmbedFn], k: int, holdout_frac: float,
                      seed: int, truth=None, reference: tuple[list[str], list[str]] | None = None) -> pd.DataFrame:
    """Each candidate embeds corpus texts (+ reference texts, in one call) → one row of metrics."""
    rows = []
    ref_texts, ref_sub = reference if reference else ([], [])
    for name, fn in candidates.items():
        t0 = time.time()
        try:
            X = _unit(fn(list(texts) + list(ref_texts)))
        except Exception as e:  # noqa: BLE001 — a broken candidate is reported, not fatal
            rows.append({"candidate": name, "error": f"{type(e).__name__}: {e}"})
            continue
        D, R = X[:len(texts)], X[len(texts):]
        rows.append({
            "candidate": name, "dim": int(X.shape[1]),
            "journal_knn_acc": round(knn_accuracy(D, journals, k, holdout_frac, seed), 4),
            "subfield_knn_acc": round(knn_accuracy(R, ref_sub, k, holdout_frac, seed), 4) if len(R) else math.nan,
            "truth_purity": round(neighbor_purity(D, truth, k), 4) if truth is not None else math.nan,
            "seconds": round(time.time() - t0, 1), "error": ""})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ clustering bake-off
def clustering_bakeoff(emb: np.ndarray, texts: list[str], ccfg: dict, algorithms: list[str], seeds: list[int],
                       truth=None, npmi_top_n: int = 10) -> pd.DataFrame:
    from sklearn.metrics import adjusted_rand_score

    from atlas.cluster import fit_labels

    doc_tokens = [set(tokenize(t)) for t in texts]
    rows, reference = [], None
    for algo in algorithms:
        if algo == "leiden" and not _has_module("igraph"):
            rows.append({"algorithm": algo, "error": "igraph not installed (uv sync --extra leiden)"})
            continue
        if algo == "hdbscan_fast" and not _has_module("fast_hdbscan"):
            rows.append({"algorithm": algo, "error": "fast_hdbscan not installed (uv sync --extra fast)"})
            continue
        cfg_a = copy.deepcopy(ccfg)
        cfg_a["algorithm"] = "leiden" if algo == "leiden" else "hdbscan"
        cfg_a["hdbscan_backend"] = "fast" if algo == "hdbscan_fast" else "sklearn"
        runs, secs = [], []
        for s in seeds:
            t0 = time.time()
            runs.append(fit_labels(emb, cfg_a, s)[0])
            secs.append(time.time() - t0)
        first = runs[0]
        reference = first if reference is None else reference
        ids = sorted(set(first.tolist()) - {-1})
        terms = topic_terms({t: [texts[i] for i in np.where(first == t)[0]] for t in ids}, npmi_top_n,
                            int(ccfg["ctfidf_max_docs_per_topic"]), seeds[0])
        rows.append({
            "algorithm": algo, "n_topics": int(np.median([len(set(r.tolist()) - {-1}) for r in runs])),
            "unassigned": round(float(np.mean([(r < 0).mean() for r in runs])), 4),
            "ari_stability": round(ari_stability(runs), 4),
            "ari_vs_first": round(float(adjusted_rand_score(reference, first)), 4),
            "purity": round(purity(first, truth), 4) if truth is not None else math.nan,
            "npmi": round(npmi_coherence(terms, doc_tokens, npmi_top_n), 4),
            "seconds_per_run": round(float(np.mean(secs)), 1), "error": ""})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ report
def _table(df: pd.DataFrame) -> list[str]:
    if df is None or df.empty:
        return ["(not run)"]
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join("" if (isinstance(v, float) and math.isnan(v)) else str(v) for v in r) + " |")
    return out


def render_report(emb_df: pd.DataFrame | None, clu_df: pd.DataFrame | None, meta: dict) -> str:
    lines = ["# Bake-off report", "", *[f"- {k}: {v}" for k, v in meta.items()], "",
             "## Embedding models", "", *_table(emb_df), "", "## Clustering", "", *_table(clu_df), ""]
    score_cols = [c for c in ("journal_knn_acc", "subfield_knn_acc", "truth_purity")
                  if emb_df is not None and c in emb_df and emb_df[c].notna().any()]
    if score_cols:                                 # mean of the scores this run has (subfield/purity when present)
        ranked = emb_df.assign(_mean=emb_df[score_cols].mean(axis=1, skipna=True)).sort_values(
            "_mean", ascending=False, kind="stable")
        best = ranked.iloc[0]
        lines.append(f"Best embedding by the mean of {', '.join(score_cols)}: **{best['candidate']}** "
                     f"({best['_mean']:.4f}) — advisory: check the per-column numbers before switching models")
    if clu_df is not None and "ari_stability" in clu_df and clu_df["ari_stability"].notna().any():
        ok = clu_df[clu_df["ari_stability"] >= 0.8]
        key = "purity" if ok["purity"].notna().any() else "npmi"
        if len(ok):
            best = ok.sort_values(key, ascending=False).iloc[0]
            lines.append(f"Best stable clustering (ARI ≥ 0.8) by {key}: **{best['algorithm']}** ({best[key]})")
        else:
            lines.append("No clustering algorithm reached ARI stability ≥ 0.8.")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ CLI glue
def candidate_fn(cfg: dict, cand: dict) -> EmbedFn:
    """Embedding function for one bakeoff.embedding_candidates entry (api/local go through the store)."""
    from atlas.embed import embed_texts, lite_embed

    if cand["provider"] == "lite":
        return lambda texts: lite_embed(texts, cfg["embedding"]["lite"], int(cfg["pipeline"]["seed"]))
    c2 = copy.deepcopy(cfg)
    c2["embedding"]["provider"] = cand["provider"]
    block = c2["embedding"][cand["provider"]]
    if cand["model"]:
        block["model"] = cand["model"]
    if cand["provider"] == "api":
        if cand["base_url"]:
            block["base_url"] = cand["base_url"]
        block["dimensions"] = cand["dimensions"]          # None = not sent (bge-m3) — never inherit the default 1024
        block["store_id"] = cand.get("store_id")          # None → the runner's "api|<model>|<dimensions>"
    return lambda texts: embed_texts(c2, texts)


def run_bakeoff(cfg: dict, kind: str, truth_path: str | Path | None = None) -> str:
    from atlas.checkpoints import load_aligned

    work = Path(cfg["pipeline"]["work_dir"])
    bcfg, seed = cfg["bakeoff"], int(cfg["pipeline"]["seed"])
    docs, all_emb = load_aligned(work)
    rng = np.random.default_rng(seed)
    pick = np.sort(rng.choice(len(docs), min(int(bcfg["sample"]), len(docs)), replace=False))
    sample = docs.iloc[pick].reset_index(drop=True)
    truth = None
    if truth_path:
        t = pd.read_csv(truth_path).set_index("article_id")["topic"]
        truth = sample["article_id"].map(t).fillna("?").astype(str).to_numpy()
    texts = sample["doc_text"].tolist()
    emb_df = clu_df = None
    meta = {"work_dir": str(work), "sample": len(sample), "k": bcfg["k"], "seeds": bcfg["seeds"]}
    if kind in ("embedding", "all"):
        cands = {c["name"]: candidate_fn(cfg, c) for c in bcfg["embedding_candidates"]} or {
            "lite (configured)": candidate_fn(cfg, {"provider": "lite"})}
        reference = None
        try:
            from atlas.openalex import load_reference

            ref, _ = load_reference(cfg)
            reference = ((ref["title"] + " . " + ref["abstract"]).tolist(), ref["subfield_id"].astype(str).tolist())
        except Exception as e:  # noqa: BLE001 — subfield accuracy is optional
            meta["subfield_reference"] = f"unavailable ({type(e).__name__})"
        emb_df = embedding_bakeoff(texts, sample["journal_name"].astype(str).to_numpy(), cands, int(bcfg["k"]),
                                   float(bcfg["holdout_frac"]), seed, truth, reference)
    if kind in ("clustering", "all"):
        emb = all_emb[pick]
        clu_df = clustering_bakeoff(emb, texts, cfg["clustering"], list(bcfg["algorithms"]),
                                    [int(s) for s in bcfg["seeds"]], truth, int(bcfg["npmi_top_n"]))
    return render_report(emb_df, clu_df, meta)
