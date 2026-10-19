"""Editorial review: merge suggestions (LLM task "merge") and the quarterly label spot check.

Merge suggestions — topic pairs whose centroids are nearly identical (cosine ≥
labeling.merge.min_similarity, most similar first, at most labeling.merge.max_pairs) are shown to
the LLM with names, keywords and representative titles (prompts/topic_merge.th.md) → {same_topic,
reason}. Nothing is merged automatically: a merge changes stable ids and a wrong one distorts the
whole map. Without an LLM (labeling.provider off, or no llm.tasks.merge.model) the pairs are listed
by similarity only. Output: work/05_merge_suggestions.

`atlas review export` → output/review/<release>_label_review.csv (UTF-8 with BOM so Excel shows Thai):
a reproducible sample of review.sample_size topics — every keyword-fallback label and every possible
duplicate first, then a seeded random draw of the rest (topics an editor already fixed are skipped) —
with empty columns for the editor. `atlas review import FILE` upserts the corrected names into
labeling.overrides_path, which the label step applies every quarter.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel

from atlas.io_utils import read_table, write_table
from atlas.label import OVERRIDE_COLUMNS, load_overrides, parse_topic_id, topic_titles
from atlas.lineage import topic_code
from atlas.llm_runner import LlmItem, LlmJob, run_job
from atlas.prompts import load_prompt, prompt_version, render_prompt
from atlas.state import current_release

PROMPT_NAME = "topic_merge.th"
MERGE_COLUMNS = ["topic_a", "topic_b", "similarity", "same_topic", "reason", "source"]
REVIEW_COLUMNS = ["topic_id", "name_th", "name_en", "label_source", "size", "status", "keywords", "sample_titles",
                  "possible_duplicate", "why_in_sample", "ok", "name_th_fixed", "name_en_fixed", "reviewer", "note"]


class MergeOut(BaseModel):
    same_topic: bool
    reason: str = ""


def merge_candidates(cfg: dict) -> list[tuple[int, int, float]]:
    """(topic a, topic b, centroid cosine) for the most similar pairs above labeling.merge.min_similarity."""
    work, mcfg = Path(cfg["pipeline"]["work_dir"]), cfg["labeling"]["merge"]
    C = np.load(work / "04_centroids.npy")
    ids = json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))
    S = C @ C.T
    iu = np.triu_indices(len(ids), k=1)
    sims = S[iu]
    keep = np.where(sims >= float(mcfg["min_similarity"]))[0]
    keep = keep[np.argsort(-sims[keep], kind="stable")][: int(mcfg["max_pairs"])]
    return [(int(ids[iu[0][k]]), int(ids[iu[1][k]]), round(float(sims[k]), 4)) for k in keep]


def _uses_llm(cfg: dict) -> bool:
    return cfg["labeling"]["provider"] == "llm" and bool(cfg["llm"]["tasks"]["merge"]["model"])


def merge_job(cfg: dict) -> LlmJob:
    work = Path(cfg["pipeline"]["work_dir"])
    labels = read_table(work / "05_labels.parquet").set_index("topic_id")
    info = read_table(work / "04_topic_info.parquet").set_index("topic_id")
    template = load_prompt(PROMPT_NAME, cfg["llm"]["prompts_dir"])
    pairs = merge_candidates(cfg)
    titles = topic_titles(cfg, int(cfg["review"]["n_titles"])) if pairs else {}
    items = []
    for a, b, _ in pairs:
        side = {}
        for tag, t in (("a", a), ("b", b)):
            side[f"name_{tag}"] = f"{labels.loc[t, 'name_th']} ({labels.loc[t, 'name_en']})"
            side[f"keywords_{tag}"] = info.loc[t, "top_keywords"]
            side[f"titles_{tag}"] = "\n".join(f"- {x}" for x in titles.get(t, []))
        items.append(LlmItem(f"{topic_code(a)}|{topic_code(b)}", render_prompt(template, **side),
                             {"same_topic": None, "reason": ""}))
    return LlmJob("merge", MergeOut, prompt_version(template), items)


def suggest_merges(cfg: dict, llm=None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    pairs = merge_candidates(cfg) if cfg["labeling"]["merge"]["enabled"] else []
    rows = [{"topic_a": a, "topic_b": b, "similarity": s, "same_topic": None, "reason": "", "source": "similarity"}
            for a, b, s in pairs]
    stats = None
    if pairs and (llm is not None or _uses_llm(cfg)):
        results, stats = run_job(cfg, merge_job(cfg), llm)
        for r in rows:
            res = results[f"{topic_code(r['topic_a'])}|{topic_code(r['topic_b'])}"]
            r.update(same_topic=res.output["same_topic"], reason=res.output["reason"],
                     source="fallback" if res.source == "fallback" else "llm")
    elif pairs:
        print("[label] merge suggestions by similarity only (set labeling.provider: llm and llm.tasks.merge.model "
              "for an LLM opinion)")
    out = pd.DataFrame(rows, columns=MERGE_COLUMNS)
    out["same_topic"] = out["same_topic"].astype(object)
    write_table(out, work / "05_merge_suggestions.parquet")
    (work / "05_merge_meta.json").write_text(json.dumps({"llm": stats}, ensure_ascii=False), encoding="utf-8")
    flagged = sum(1 for v in out["same_topic"] if v is None or bool(v))     # unknown counts as "look at it"
    print(f"[label] {len(out)} near-duplicate topic pairs, {flagged} to review")
    return out


# ---------------------------------------------------------------------- review export / import
def export_review(cfg: dict, out: str | Path | None = None, n: int | None = None) -> Path:
    work = Path(cfg["pipeline"]["work_dir"])
    labels = read_table(work / "05_labels.parquet")
    info = read_table(work / "04_topic_info.parquet")[["topic_id", "size", "top_keywords"]]
    df = labels.merge(info, on="topic_id", how="left")
    em_path = work / "07_emerging.parquet"
    status = read_table(em_path).set_index("topic_id")["status"].to_dict() if em_path.exists() else {}
    names = df.set_index("topic_id")["name_th"].to_dict()
    dup: dict[int, str] = {}
    mpath = work / "05_merge_suggestions.parquet"
    if mpath.exists():
        for m in read_table(mpath).itertuples():
            if pd.notna(m.same_topic) and not bool(m.same_topic):     # the LLM said: different topics
                continue
            dup.setdefault(int(m.topic_a), f"{topic_code(m.topic_b)} {names.get(int(m.topic_b), '')}")
            dup.setdefault(int(m.topic_b), f"{topic_code(m.topic_a)} {names.get(int(m.topic_a), '')}")
    n = int(n or cfg["review"]["sample_size"])
    why: dict[int, str] = {}
    if cfg["labeling"]["provider"] == "llm":
        for t in df.loc[df["label_source"] == "keywords", "topic_id"]:
            why[int(t)] = "fallback"
    for t in dup:
        why.setdefault(t, "duplicate")
    rest = df.loc[~df["topic_id"].isin(list(why)) & (df["label_source"] != "override"), "topic_id"].astype(int)
    rng = np.random.default_rng(int(cfg["pipeline"]["seed"]))
    k = max(0, n - len(why))
    for t in rng.permutation(rest.to_numpy())[:k]:
        why[int(t)] = "random"
    chosen = df[df["topic_id"].isin(list(why))].sort_values("topic_id")
    titles = topic_titles(cfg, int(cfg["review"]["n_titles"]))
    rows = [{"topic_id": topic_code(r.topic_id), "name_th": r.name_th, "name_en": r.name_en,
             "label_source": r.label_source, "size": int(r.size), "status": status.get(int(r.topic_id), ""),
             "keywords": r.top_keywords, "sample_titles": " | ".join(titles.get(int(r.topic_id), [])),
             "possible_duplicate": dup.get(int(r.topic_id), ""), "why_in_sample": why[int(r.topic_id)],
             "ok": "", "name_th_fixed": "", "name_en_fixed": "", "reviewer": "", "note": ""}
            for r in chosen.itertuples()]
    path = Path(out) if out else (Path(cfg["pipeline"]["output_dir"]) / "review"
                                  / f"{current_release(cfg)}_label_review.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=REVIEW_COLUMNS).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def import_review(cfg: dict, path: str | Path) -> dict:
    target = cfg["labeling"]["overrides_path"]
    if not target:
        raise ValueError("set labeling.overrides_path in the config (e.g. ./registry/label_overrides.csv)")
    rev = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    missing = [c for c in REVIEW_COLUMNS if c not in rev.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}; expected columns: {', '.join(REVIEW_COLUMNS)}")
    fixed = rev[(rev["name_th_fixed"].str.strip() != "") | (rev["name_en_fixed"].str.strip() != "")]
    ov = load_overrides(target)
    today = date.today().isoformat()
    old = ov.set_index("topic_id").to_dict("index")
    rows = []
    for r in fixed.itertuples():
        tid = parse_topic_id(r.topic_id, f"{path}: row {r.Index + 2}")
        prev = old.get(tid, {})
        # a blank field keeps the existing override's value: fixing only name_en must not revert name_th
        rows.append({"topic_id": tid, "name_th": r.name_th_fixed.strip() or prev.get("name_th", ""),
                     "name_en": r.name_en_fixed.strip() or prev.get("name_en", ""),
                     "description": prev.get("description", ""),
                     "reviewer": r.reviewer.strip() or prev.get("reviewer", ""), "reviewed_at": today,
                     "note": r.note.strip() or prev.get("note", "")})
    new = pd.DataFrame(rows, columns=OVERRIDE_COLUMNS)
    merged = pd.concat([ov[~ov["topic_id"].isin(new["topic_id"])], new], ignore_index=True).sort_values("topic_id")
    merged["topic_id"] = merged["topic_id"].map(topic_code)
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(target, index=False, encoding="utf-8-sig")
    return {"applied": len(new), "reviewed": len(rev), "overrides_total": len(merged), "path": str(target)}
