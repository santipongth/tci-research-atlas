"""Phase 7b — Export web-ready JSON + analyst CSVs + manifest.

Output (output_dir):
  atlas_data.json   — nodes/links/groups + per-topic emerging & forecast (for the web atlas)
  topics.csv        — topic catalogue
  emerging.csv      — emerging metrics per topic
  forecasts.csv     — forecast per topic
  manifest.json     — pipeline version, counts, dates
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .io_utils import read_table, write_table

# categorical palette for coarse groups (matches the web atlas style)
PALETTE = ["#E5484D", "#8E4EC6", "#3E63DD", "#F76B15", "#30A46C", "#0091FF", "#E93D82",
           "#D6409F", "#AB4ABA", "#12A594", "#00A2C7", "#46A758", "#C44A6B", "#6E56CF",
           "#AD7F58", "#5B5BD6", "#FFB224", "#FF8FA3", "#0E9F6E", "#697177"]


def _git_hash() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5).stdout.strip() or "nogit"
    except Exception:
        return "nogit"


def export(cfg: dict) -> dict:
    work = Path(cfg["pipeline"]["work_dir"])
    outdir = Path(cfg["pipeline"]["output_dir"])
    outdir.mkdir(parents=True, exist_ok=True)

    info = read_table(work / "04_topic_info.parquet")
    labels = read_table(work / "05_labels.parquet")
    layout_df = read_table(work / "09_layout.parquet")
    edges = read_table(work / "09_edges.parquet")
    emerging_df = read_table(work / "07_emerging.parquet")
    fc = read_table(work / "08_forecasts.parquet")
    meta = pd.read_json(work / "06_meta.json", typ="series")

    labels = labels[labels["level"] == "fine"].set_index("topic_id")
    labels = labels[~labels.index.duplicated(keep="last")]  # keep newest prompt_hash
    em = emerging_df.set_index("topic_id")
    fcm = fc.set_index("topic_id") if len(fc) else pd.DataFrame()

    # ---- group (coarse) table ----
    groups = []
    coarse_ids = sorted(info["coarse_topic"].unique())
    color_of = {cid: PALETTE[i % len(PALETTE)] for i, cid in enumerate(coarse_ids)}
    sizes = info.groupby("coarse_topic")["size"].sum()
    for cid in coarse_ids:
        members = info[info["coarse_topic"] == cid].sort_values("size", ascending=False)
        # ตั้งชื่อกลุ่มตาม topic ที่ใหญ่สุดในกลุ่ม
        big = members["topic_id"].iloc[0]
        top = labels["name_th"].loc[big] if big in labels.index else f"กลุ่ม {cid}"
        top_en = labels["name_en"].loc[big] if big in labels.index else f"Group {cid}"
        groups.append({
            "id": f"g{cid}", "th": top, "en": top_en,
            "color": color_of[cid], "articles": int(sizes[cid]),
        })
    groups.sort(key=lambda g: -g["articles"])
    for i, g in enumerate(groups):
        g["rank"] = i + 1

    # ---- nodes ----
    nodes = []
    for _, row in layout_df.iterrows():
        if row["kind"] == "group":
            cid = int(row["id"])
            g = next(g for g in groups if g["id"] == f"g{cid}")
            nodes.append({**g, "nodeId": g["id"], "kind": "group",
                          "x": row["x"], "y": row["y"], "r": row["r"],
                          "nTopics": int((info["coarse_topic"] == cid).sum())})
        else:
            tid = int(row["id"])
            lb = labels.loc[tid] if tid in labels.index else None
            e = em.loc[tid] if tid in em.index else None
            f = fcm.loc[tid] if len(fcm) and tid in fcm.index else None
            nodes.append({
                "nodeId": f"t{tid}", "kind": "topic",
                "group": f"g{int(row['parent'])}",
                "th": lb["name_th"] if lb is not None else f"หัวข้อ {tid}",
                "en": lb["name_en"] if lb is not None else f"Topic {tid}",
                "description": lb["description"] if lb is not None else "",
                "keywords": lb["keywords"] if lb is not None else "",
                "articles": int(info.loc[info["topic_id"] == tid, "size"].iloc[0]),
                "color": color_of[int(row["parent"])],
                "x": row["x"], "y": row["y"], "r": row["r"],
                "status": e["status"] if e is not None else "STABLE",
                "emerging_score": round(float(e["emerging_score"]), 1) if e is not None else None,
                "cagr_recent": round(float(e["cagr_recent"]), 3) if e is not None else None,
                "burst_years": e["burst_years"] if e is not None else "",
                "forecast": ({
                    "model": f["model"], "backtest_mape": f["backtest_mape"],
                    "hist_years": json.loads(f["hist_years"]),
                    "hist_counts": json.loads(f["hist_counts"]),
                    "fc_years": json.loads(f["fc_years"]),
                    "fc_mean": json.loads(f["fc_mean"]),
                    "fc_lo": json.loads(f["fc_lo"]),
                    "fc_hi": json.loads(f["fc_hi"]),
                } if f is not None and cfg["export"]["include_forecast_in_json"] else None),
            })

    links = [{"s": f"t{int(r['s'])}", "t": f"t{int(r['t'])}", "w": r["w"]} for _, r in edges.iterrows()]

    atlas = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_version": _git_hash(),
            "last_complete_year": int(meta["last_complete_year"]),
            "total_articles": int(info["size"].sum()),
            "total_topics": int(len(info)),
            "total_groups": len(groups),
        },
        "groups": groups,
        "nodes": nodes,
        "links": links,
    }
    (outdir / "atlas_data.json").write_text(
        json.dumps(atlas, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- analyst CSVs ----
    if "csv" in cfg["export"]["formats"]:
        topics_csv = info.merge(labels.reset_index()[["topic_id", "name_th", "name_en", "description", "keywords"]],
                                on="topic_id", how="left")
        topics_csv.to_csv(outdir / "topics.csv", index=False)
        emerging_df.to_csv(outdir / "emerging.csv", index=False)
        fc.to_csv(outdir / "forecasts.csv", index=False)

    manifest = {
        "pipeline_version": _git_hash(),
        "generated_at": atlas["meta"]["generated_at"],
        "config_emerging": cfg["emerging"],
        "counts": atlas["meta"],
        "artifacts": sorted(p.name for p in outdir.iterdir()),
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # stash centroids for next run's novelty metric
    prev = work / "prev"
    prev.mkdir(exist_ok=True)
    src = work / "04_centroids.npy"
    if src.exists():
        shutil.copy(src, prev / "centroids.npy")
        shutil.copy(work / "04_centroid_ids.json", prev / "centroid_ids.json")

    print(f"[export] -> {outdir}/atlas_data.json (+ topics.csv, emerging.csv, forecasts.csv, manifest.json)")
    return atlas
