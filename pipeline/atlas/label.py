"""Topic labeling (topic-level LLM task "label").

labeling.provider = llm: author keywords + c-TF-IDF words + representative titles (nearest to the
centroid, diversified with MMR) → prompts/topic_label.th.md → the LLM runner (atlas/llm_runner.py:
cache keyed by model + prompt version + prompt, JSON repairs, keyword fallback, budget, stop).
labeling.provider = off: names from the topic's most distinctive author keywords (TH and EN).
Either way the editors' file labeling.overrides_path (CSV keyed by the stable topic id T000123)
wins, so corrections stick across quarters.

Outputs: work/05_labels (level, topic_id, name_th, name_en, description, keywords, cache_key,
label_source ∈ llm | keywords | override) and work/05_labels_meta.json (counts + LLM spend).
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
from atlas.thai import thai_ratio

PROMPT_NAME = "topic_label.th"
LABEL_COLUMNS = ["level", "topic_id", "name_th", "name_en", "description", "keywords", "cache_key", "label_source"]
OVERRIDE_COLUMNS = ["topic_id", "name_th", "name_en", "description", "reviewer", "reviewed_at", "note"]


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


def label_job(cfg: dict) -> LlmJob:
    """One LLM item per topic (registered in llm_runner.JOBS for `atlas llm --dry-run`)."""
    work = Path(cfg["pipeline"]["work_dir"])
    info = read_table(work / "04_topic_info.parquet")
    template = load_prompt(PROMPT_NAME, cfg["llm"]["prompts_dir"])
    titles = topic_titles(cfg)
    items = []
    for r in info.itertuples():
        tid = int(r.topic_id)
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
    info = read_table(work / "04_topic_info.parquet")
    provider = cfg["labeling"]["provider"]
    rows, stats = [], {"from_cache": 0, "generated": 0, "repaired": 0, "fallback": 0, "cost_usd": 0.0, "model": ""}
    if provider == "llm":
        job = label_job(cfg)
        results, stats = run_job(cfg, job, llm)
        for r in info.itertuples():
            code = topic_code(int(r.topic_id))
            res = results[code]
            out = res.output
            kws = out.get("keywords", [])
            rows.append({"level": "fine", "topic_id": int(r.topic_id), "name_th": out["name_th"],
                         "name_en": out["name_en"], "description": out.get("description", ""),
                         "keywords": "; ".join(kws) if isinstance(kws, list) else str(kws),
                         "cache_key": res.key or "fallback",
                         "label_source": "llm" if res.source != "fallback" else "keywords"})
    else:
        for r in info.itertuples():
            fb = _fallback(r.top_keywords, r.top_terms, int(r.topic_id))
            rows.append({"level": "fine", "topic_id": int(r.topic_id), **fb, "keywords": "; ".join(fb["keywords"]),
                         "cache_key": "fallback", "label_source": "keywords"})
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
    meta = {"provider": provider, "model_id": stats["model"], "topics": len(out),
            "from_cache": stats["from_cache"], "generated": stats["generated"], "repaired": stats["repaired"],
            "fallback": int((out["cache_key"] == "fallback").sum()) if provider == "llm" else 0,
            "overrides": applied, "unknown_overrides": unknown, "cost_usd": stats["cost_usd"]}
    (work / "05_labels_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[label] {len(out)} topics: {meta['generated']} new, {meta['from_cache']} cached, "
          f"{meta['fallback']} keyword fallback, {applied} editor overrides")
    if cfg["labeling"]["merge"]["enabled"]:
        from atlas.review import suggest_merges  # local import: atlas.review imports this module

        suggest_merges(cfg)
    return out
