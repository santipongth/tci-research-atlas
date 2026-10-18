"""Export web-ready JSON (atlas_data.json, schema 1.1) + analyst CSVs + manifest.

1.1 = the v1 contract read by web/src/lib/loader.ts, plus per topic:
  status in EMERGING | WATCH | HOT | DECLINING | STABLE | LOW_DATA   (definition_version from config, 3)
  share_growth(_lo/_hi), n_journals_R, n_orgs_R, journal_driven, orgs_unverified, coherence, forecast_uncertain
  forecast is non-null only when the skill gate `show` is true
  meta adds as_of_year, trimmed_years, n_orgs_unverified (additive — schema stays 1.1)
Strict JSON: NaN/Infinity become null (browsers reject NaN in JSON).
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table

SCHEMA_VERSION = "1.1"
# Thai fallback prefixes (written with code point names, never literal escapes)
_GROUP_TH = ("\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER SARA U}"
             "\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER MO MA} ")
_TOPIC_TH = ("\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER WO WAEN}"
             "\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER O ANG} ")
# categorical palette for coarse groups (matches the current web atlas)
PALETTE = ["#E5484D", "#8E4EC6", "#3E63DD", "#F76B15", "#30A46C", "#0091FF", "#E93D82",
           "#D6409F", "#AB4ABA", "#12A594", "#00A2C7", "#46A758", "#C44A6B", "#6E56CF",
           "#AD7F58", "#5B5BD6", "#FFB224", "#FF8FA3", "#0E9F6E", "#697177"]


def _git_hash() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5).stdout.strip() or "nogit"
    except Exception:  # noqa: BLE001
        return "nogit"


def clean_json(obj):
    if isinstance(obj, bool | np.bool_):
        return bool(obj)
    if isinstance(obj, int | np.integer):
        return int(obj)
    if isinstance(obj, float | np.floating):
        f = float(obj)
        return f if math.isfinite(f) else None
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [clean_json(v) for v in obj]
    return obj


def _r(v, nd: int = 3):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, nd) if math.isfinite(f) else None


def fine_labels(labels: pd.DataFrame) -> pd.DataFrame:
    """One fine-level label row per topic (latest wins) - shared by JSON and CSV."""
    return labels[labels["level"] == "fine"].drop_duplicates("topic_id", keep="last")


def _is_true(v) -> bool:
    return bool(pd.notna(v) and bool(v))


def build_atlas(info: pd.DataFrame, labels: pd.DataFrame, layout_df: pd.DataFrame, edges: pd.DataFrame,
                em: pd.DataFrame, fc: pd.DataFrame, meta: dict, n_articles: int, include_forecast: bool,
                definition_version: int) -> dict:
    labels = fine_labels(labels).set_index("topic_id")
    em = em.set_index("topic_id")
    fcm = fc.set_index("topic_id") if len(fc) else pd.DataFrame()
    info_i = info.set_index("topic_id")

    coarse_ids = sorted(int(c) for c in info["coarse_topic"].unique())
    color_of = {cid: PALETTE[i % len(PALETTE)] for i, cid in enumerate(coarse_ids)}
    sizes = info.groupby("coarse_topic")["size"].sum()
    groups = []
    for cid in coarse_ids:
        big = int(info[info["coarse_topic"] == cid].sort_values("size", ascending=False)["topic_id"].iloc[0])
        groups.append({"id": f"g{cid}",
                       "th": labels["name_th"].get(big, f"{_GROUP_TH}{cid}"),
                       "en": labels["name_en"].get(big, f"Group {cid}"),
                       "color": color_of[cid], "articles": int(sizes[cid])})
    groups.sort(key=lambda g: -g["articles"])
    for i, g in enumerate(groups):
        g["rank"] = i + 1
    by_gid = {g["id"]: g for g in groups}

    nodes = []
    for _, row in layout_df.iterrows():
        if row["kind"] == "group":
            cid = int(row["id"])
            g = by_gid[f"g{cid}"]
            nodes.append({**g, "nodeId": g["id"], "kind": "group", "x": row["x"], "y": row["y"], "r": row["r"],
                          "nTopics": int((info["coarse_topic"] == cid).sum())})
            continue
        tid = int(row["id"])
        lb = labels.loc[tid] if tid in labels.index else None
        e = em.loc[tid] if tid in em.index else None
        f = fcm.loc[tid] if len(fcm) and tid in fcm.index else None
        low_data = e is None or e["status"] == "LOW_DATA"
        passes_gate = f is not None and _is_true(f["show"]) and not low_data   # no trend claim → no forecast
        show = passes_gate and include_forecast
        nodes.append({
            "nodeId": f"t{tid}", "kind": "topic", "group": f"g{int(row['parent'])}",
            "th": lb["name_th"] if lb is not None else f"{_TOPIC_TH}{tid}",
            "en": lb["name_en"] if lb is not None else f"Topic {tid}",
            "description": lb["description"] if lb is not None else "",
            "keywords": lb["keywords"] if lb is not None else "",
            "articles": int(info_i.loc[tid, "size"]),
            "color": color_of[int(row["parent"])],
            "x": row["x"], "y": row["y"], "r": row["r"],
            "status": e["status"] if e is not None else "LOW_DATA",
            "emerging_score": _r(e["emerging_score"], 1) if e is not None else None,
            "cagr_recent": _r(e["cagr_recent"]) if e is not None else None,
            "burst_years": (e["burst_years"] or "") if e is not None else "",
            "share_growth": _r(e["share_growth"]) if e is not None else None,
            "share_growth_lo": _r(e["share_growth_lo"]) if e is not None else None,
            "share_growth_hi": _r(e["share_growth_hi"]) if e is not None else None,
            "n_journals_R": int(e["n_journals_R"]) if e is not None else 0,
            "n_orgs_R": int(e["n_orgs_R"]) if e is not None else 0,
            "journal_driven": bool(e["journal_driven"]) if e is not None else False,
            "orgs_unverified": bool(e["orgs_unverified"]) if e is not None else False,
            "coherence": _r(info_i.loc[tid, "coherence"]),
            "forecast": ({
                "model": f["model"], "backtest_mape": _r(f["backtest_mape"], 2), "mase": _r(f["mase"]),
                "skill_vs_naive": _r(f["skill_vs_naive"]),
                "hist_years": json.loads(f["hist_years"]), "hist_counts": json.loads(f["hist_counts"]),
                "fc_years": json.loads(f["fc_years"]), "fc_mean": json.loads(f["fc_mean"]),
                "fc_lo": json.loads(f["fc_lo"]), "fc_hi": json.loads(f["fc_hi"]),
            } if show else None),
            "forecast_uncertain": bool((f is not None or low_data) and not passes_gate),
        })

    assigned = int(info["size"].sum())
    atlas = {
        "meta": {
            "generated_at": datetime.now(UTC).isoformat(),
            "pipeline_version": _git_hash(),
            "schema_version": SCHEMA_VERSION,
            "definition_version": int(definition_version),
            "last_complete_year": int(meta["last_complete_year"]),
            "as_of_year": meta.get("as_of_year"),
            "trimmed_years": [int(y) for y in meta.get("trimmed_years", [])],
            "total_articles": int(n_articles),
            "assigned_articles": assigned,
            "unassigned_articles": int(n_articles) - assigned,
            "total_topics": int(len(info)),
            "total_groups": len(groups),
            "n_orgs_unverified": int(em["orgs_unverified"].astype(bool).sum()) if len(em) else 0,
        },
        "groups": groups,
        "nodes": nodes,
        "links": [{"s": f"t{int(r['s'])}", "t": f"t{int(r['t'])}", "w": r["w"]} for _, r in edges.iterrows()],
    }
    return clean_json(atlas)


def export(cfg: dict) -> dict:
    work, outdir = Path(cfg["pipeline"]["work_dir"]), Path(cfg["pipeline"]["output_dir"])
    state = Path(cfg["pipeline"]["state_dir"])
    for name in ("04_centroids.npy", "04_centroid_ids.json"):
        if not (work / name).exists():
            raise FileNotFoundError(f"export needs {work / name} (written by the cluster step); nothing was exported")
    outdir.mkdir(parents=True, exist_ok=True)
    info = read_table(work / "04_topic_info.parquet")
    labels = read_table(work / "05_labels.parquet")
    em = read_table(work / "07_emerging.parquet")
    fc = read_table(work / "08_forecasts.parquet")
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    atlas = build_atlas(info, labels, read_table(work / "09_layout.parquet"), read_table(work / "09_edges.parquet"),
                        em, fc, meta, n_articles=len(read_table(work / "02_docs.parquet")),
                        include_forecast=bool(cfg["export"]["include_forecast_in_json"]),
                        definition_version=int(cfg["emerging"]["definition_version"]))
    (outdir / "atlas_data.json").write_text(json.dumps(atlas, ensure_ascii=False, indent=1, allow_nan=False),
                                            encoding="utf-8")
    if "csv" in cfg["export"]["formats"]:
        lab = fine_labels(labels)[["topic_id", "name_th", "name_en", "description", "keywords"]]
        info.merge(lab, on="topic_id", how="left").to_csv(outdir / "topics.csv", index=False, encoding="utf-8")
        em.to_csv(outdir / "emerging.csv", index=False, encoding="utf-8")
        fc.to_csv(outdir / "forecasts.csv", index=False, encoding="utf-8")
    manifest = {
        "pipeline_version": atlas["meta"]["pipeline_version"],
        "generated_at": atlas["meta"]["generated_at"],
        "schema_version": SCHEMA_VERSION,
        "definition_version": atlas["meta"]["definition_version"],
        "config_emerging": cfg["emerging"],
        "counts": atlas["meta"],
        "artifacts": sorted(p.name for p in outdir.iterdir()),
    }
    (outdir / "manifest.json").write_text(json.dumps(clean_json(manifest), ensure_ascii=False, indent=2,
                                                     allow_nan=False), encoding="utf-8")
    prev = state / "prev"                          # next run's novelty/lineage input - persistent
    prev.mkdir(parents=True, exist_ok=True)
    shutil.copy(work / "04_centroids.npy", prev / "centroids.npy")
    shutil.copy(work / "04_centroid_ids.json", prev / "centroid_ids.json")
    print(f"[export] -> {outdir / 'atlas_data.json'} (+ csv, manifest); centroids -> {prev}")
    return atlas
