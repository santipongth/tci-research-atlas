"""Topic labeling (topic-level LLM task "label").

labeling.provider = llm: author keywords + c-TF-IDF words + representative titles (nearest to the
centroid, diversified with MMR) → prompts/topic_label.th.md → the LLM runner (atlas/llm_runner.py:
cache keyed by model + prompt version + prompt, JSON repairs, keyword fallback, budget, stop).
labeling.provider = off: names from the topic's most distinctive author keywords (TH and EN).
Either way the editors' file labeling.overrides_path (CSV keyed by the stable topic id T000123)
wins, so corrections stick across quarters.

Reuse across quarters: a topic whose lineage event is `continue` keeps the previous release's name
(label_source "reused", no LLM call) while its top author keywords + c-TF-IDF terms still overlap the set
the name was made from by >= labeling.reuse_min_jaccard (Jaccard). New, split and merged topics and
materially changed ones are named afresh; a keyword-fallback name is never kept (the LLM is asked again).
The machine names of every release (before overrides) are kept in state_dir/releases/<release>/labels.parquet
with the term set they were made from, so the comparison never drifts quarter by quarter.

Outputs: work/05_labels (level, topic_id, name_th, name_en, description, keywords, cache_key,
label_source ∈ llm | keywords | override | reused) and work/05_labels_meta.json (counts + LLM spend).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel, field_validator

from atlas.checkpoints import load_aligned
from atlas.io_utils import read_table, write_table
from atlas.lineage import topic_code
from atlas.llm_runner import LlmItem, LlmJob, run_job
from atlas.prompts import load_prompt, prompt_version, render_prompt
from atlas.state import previous_release, release_dir, work_release
from atlas.thai import thai_ratio

PROMPT_NAME = "topic_label.th"
LABEL_COLUMNS = ["level", "topic_id", "name_th", "name_en", "description", "keywords", "cache_key", "label_source"]
OVERRIDE_COLUMNS = ["topic_id", "name_th", "name_en", "description", "reviewer", "reviewed_at", "note"]
STATE_LABEL_COLUMNS = ["topic_id", "name_th", "name_en", "description", "keywords", "cache_key", "origin",
                       "label_terms"]           # origin: llm | keywords; label_terms: the set the name was made from


class LabelOut(BaseModel):
    name_th: str
    name_en: str
    description: str = ""
    keywords: list[str] = []

    @field_validator("name_th", "name_en")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name_th and name_en must not be blank")
        return v.strip()


def representative_indices(member_emb: np.ndarray, centroid: np.ndarray, n: int, lam: float) -> list[int]:
    """Maximal Marginal Relevance: close to the centroid, but not near-duplicates of each other."""
    sims = member_emb @ centroid
    chosen = [int(np.argmax(sims))]
    while len(chosen) < min(n, len(member_emb)):
        redundancy = (member_emb @ member_emb[chosen].T).max(axis=1)
        score = lam * sims - (1 - lam) * redundancy
        score[chosen] = -np.inf
        chosen.append(int(np.argmax(score)))
    return chosen


def topic_titles(cfg: dict, n: int | None = None) -> dict[int, list[str]]:
    """{topic_id: representative titles (MMR around the centroid)} — shared by label, merge, narrative, review."""
    work, lcfg = Path(cfg["pipeline"]["work_dir"]), cfg["labeling"]
    df, emb = load_aligned(work)
    labels = (df[["article_id"]].merge(read_table(work / "04_fine_topics.parquet"), on="article_id", how="left")
              ["fine_topic"].fillna(-1).astype(int).to_numpy())
    C = np.load(work / "04_centroids.npy")
    ids = json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))
    n = int(lcfg["n_repr_docs"]) if n is None else n
    out = {}
    for i, tid in enumerate(ids):
        members = np.where(labels == tid)[0]
        if len(members) == 0 or n == 0:
            out[int(tid)] = []
            continue
        idx = representative_indices(emb[members], C[i], n, float(lcfg["mmr_lambda"]))
        out[int(tid)] = df["title"].iloc[members[idx]].fillna("").astype(str).tolist()
    return out


def _fallback(top_keywords: str, top_terms: str, tid: int) -> dict:
    kws = [k for k in str(top_keywords).split("; ") if k]
    terms = [t for t in str(top_terms).split("; ") if t]
    th = [k for k in kws if thai_ratio(k) > 0.5][:2] or [t for t in terms if thai_ratio(t) > 0.5][:3]
    en = [k for k in kws if thai_ratio(k) <= 0.5][:2] or [t for t in terms if thai_ratio(t) <= 0.5][:3]
    return {"name_th": " / ".join(th) or f"หัวข้อ {tid}", "name_en": " / ".join(en) or f"Topic {tid}",
            "description": "", "keywords": kws[:6]}


def label_terms(top_keywords, top_terms) -> set[str]:
    """A topic's top author keywords + c-TF-IDF terms (04_topic_info), lowercased — what a name is made from."""
    return {x.strip().lower() for s in (top_keywords, top_terms) for x in str(s or "").split(";") if x.strip()}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def _terms_text(terms: set[str]) -> str:
    return "; ".join(sorted(terms))


def reuse_plan(cfg: dict, info: pd.DataFrame, release: str | None = None) -> dict[int, dict]:
    """{topic_id: the previous release's machine label} for the topics that keep their name this release."""
    work = Path(cfg["pipeline"]["work_dir"])
    prev = previous_release(cfg, release or work_release(cfg))
    path = release_dir(cfg, prev) / "labels.parquet" if prev else None
    try:
        lin = read_table(work / "04_lineage.parquet")
        old = read_table(path) if path is not None else None
    except FileNotFoundError:
        return {}
    if old is None:
        return {}
    cont = set(lin.loc[lin["event"] == "continue", "topic_id"].astype(int))
    old = old.drop_duplicates("topic_id", keep="last").set_index("topic_id")
    thr = float(cfg["labeling"]["reuse_min_jaccard"])
    plan = {}
    for r in info.itertuples():
        tid = int(r.topic_id)
        if tid not in cont or tid not in old.index or str(old.loc[tid, "origin"]) != "llm":
            continue
        made_from = {x for x in str(old.loc[tid, "label_terms"]).split("; ") if x}
        if jaccard(label_terms(r.top_keywords, r.top_terms), made_from) >= thr:
            plan[tid] = old.loc[tid].to_dict()
    return plan


def label_job(cfg: dict, skip: set[int] | None = None) -> LlmJob:
    """One LLM item per topic that needs a name (registered in llm_runner.JOBS for `atlas llm --dry-run`);
    skip: topics that keep the previous release's name (default: reuse_plan)."""
    work = Path(cfg["pipeline"]["work_dir"])
    info = read_table(work / "04_topic_info.parquet")
    skip = set(reuse_plan(cfg, info)) if skip is None else skip
    template = load_prompt(PROMPT_NAME, cfg["llm"]["prompts_dir"])
    titles = topic_titles(cfg)
    items = []
    for r in info.itertuples():
        tid = int(r.topic_id)
        if tid in skip:
            continue
        prompt = render_prompt(template, keywords=r.top_keywords, terms=r.top_terms,
                               titles="\n".join(f"- {t}" for t in titles.get(tid, [])))
        items.append(LlmItem(topic_code(tid), prompt, _fallback(r.top_keywords, r.top_terms, tid)))
    return LlmJob("label", LabelOut, prompt_version(template), items)


def parse_topic_id(value: str, where: str = "") -> int:
    """'T000123' / 't123' / '123' → 123; a clear error naming the place (CSV row) and the value otherwise."""
    text = str(value).strip()
    digits = text[1:] if text[:1] in "Tt" else text
    if not digits.isdigit():
        raise ValueError(f"{where + ': ' if where else ''}topic_id {text!r} is not T000123 or an integer")
    return int(digits)


def load_overrides(path: str | Path | None) -> pd.DataFrame:
    """Editors' corrections (CSV, UTF-8 with or without BOM): topic_id (T000123 or 123), name_th, name_en, …"""
    if not path or not Path(path).exists():
        return pd.DataFrame(columns=OVERRIDE_COLUMNS)
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    missing = {"topic_id", "name_th", "name_en"} - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    for c in OVERRIDE_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df["topic_id"] = [parse_topic_id(v, f"{path}: row {i + 2}") for i, v in enumerate(df["topic_id"])]
    return df[OVERRIDE_COLUMNS].drop_duplicates("topic_id", keep="last")


def label(cfg: dict, llm=None) -> pd.DataFrame:
    """llm: an object with .model_id and .chat(messages) (tests); None → the configured endpoint, if needed."""
    work = Path(cfg["pipeline"]["work_dir"])
    release = work_release(cfg)          # refuse before any LLM call when pipeline.release names another release
    info = read_table(work / "04_topic_info.parquet")
    provider = cfg["labeling"]["provider"]
    reuse = reuse_plan(cfg, info, release)
    rows, machine, results = [], [], {}
    stats = {"from_cache": 0, "generated": 0, "repaired": 0, "fallback": 0, "cost_usd": 0.0, "model": ""}
    if provider == "llm":
        job = label_job(cfg, skip=set(reuse))
        if job.items:
            results, stats = run_job(cfg, job, llm)
        else:                                              # every name reused: no runner, no endpoint needed
            stats["model"] = llm.model_id if llm is not None else cfg["llm"]["tasks"]["label"]["model"]
    for r in info.itertuples():
        tid = int(r.topic_id)
        made_from = _terms_text(label_terms(r.top_keywords, r.top_terms))
        if tid in reuse:                                   # last release's name: no LLM call
            o = reuse[tid]
            row = {k: "" if pd.isna(o[k]) else str(o[k]) for k in ("name_th", "name_en", "description", "keywords",
                                                                     "cache_key")}
            row["label_source"], origin, made_from = "reused", "llm", str(o["label_terms"])
        elif provider == "llm":
            res = results[topic_code(tid)]
            kws = res.output.get("keywords", [])
            row = {"name_th": res.output["name_th"], "name_en": res.output["name_en"],
                   "description": res.output.get("description", ""),
                   "keywords": "; ".join(kws) if isinstance(kws, list) else str(kws),
                   "cache_key": res.key or "fallback", "label_source": "llm" if res.source != "fallback" else "keywords"}
            origin = row["label_source"]
        else:
            fb = _fallback(r.top_keywords, r.top_terms, tid)
            row = {**fb, "keywords": "; ".join(fb["keywords"]), "cache_key": "fallback", "label_source": "keywords"}
            origin = "keywords"
        rows.append({"level": "fine", "topic_id": tid, **row})
        machine.append({"topic_id": tid, **{k: row[k] for k in STATE_LABEL_COLUMNS[1:6]}, "origin": origin,
                        "label_terms": made_from})
    out = pd.DataFrame(rows, columns=LABEL_COLUMNS)

    ov = load_overrides(cfg["labeling"]["overrides_path"])
    known = set(out["topic_id"])
    unknown = sorted(topic_code(t) for t in set(ov["topic_id"]) - known)
    applied = 0
    for o in ov[ov["topic_id"].isin(known)].itertuples():
        i = out.index[out["topic_id"] == o.topic_id][0]
        changed = False
        for col in ("name_th", "name_en", "description"):
            if str(getattr(o, col)).strip():
                out.loc[i, col] = str(getattr(o, col)).strip()
                changed = True
        if changed:
            out.loc[i, "label_source"] = "override"
            applied += 1
    if unknown:
        print(f"[label] WARNING: {len(unknown)} overrides name topics that no longer exist: {', '.join(unknown[:10])}")
    write_table(out, work / "05_labels.parquet")
    # the machine names (before overrides) for the next release's reuse — persistent, unlike work_dir
    write_table(pd.DataFrame(machine, columns=STATE_LABEL_COLUMNS), release_dir(cfg, release, create=True)
                / "labels.parquet")
    n_reused = int((out["label_source"] == "reused").sum())
    meta = {"provider": provider, "model_id": stats["model"], "topics": len(out),
            "from_cache": stats["from_cache"], "generated": stats["generated"], "repaired": stats["repaired"],
            "fallback": int((out["cache_key"] == "fallback").sum()) if provider == "llm" else 0,
            "reused": n_reused, "overrides": applied, "unknown_overrides": unknown, "cost_usd": stats["cost_usd"]}
    (work / "05_labels_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[label] {len(out)} topics: {meta['generated']} new, {meta['from_cache']} cached, {n_reused} reused "
          f"from the previous release, {meta['fallback']} keyword fallback, {applied} editor overrides")
    if cfg["labeling"]["merge"]["enabled"]:
        from atlas.review import suggest_merges  # local import: atlas.review imports this module

        suggest_merges(cfg)
    return out
