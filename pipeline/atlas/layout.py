"""Phase 7a — 2D layout of topics for the atlas map.

Positions come from UMAP 2D on fine-topic centroids (near = semantically similar).
Coarse-group hubs are placed at the size-weighted mean of their member topics.
Edges = cosine similarity between centroids above threshold.

Output: work/09_layout.parquet  (kind, id, x, y, r, parent)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .io_utils import read_table, write_table


def layout(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    lcfg = cfg["layout"]
    seed = int(cfg["pipeline"]["seed"])

    centroids = np.load(work / "04_centroids.npy")
    ids = pd.read_json(work / "04_centroid_ids.json", typ="series").tolist()
    info = read_table(work / "04_topic_info.parquet").set_index("topic_id")

    # --- 2D positions ---
    if len(ids) >= 4:
        import umap
        pos = umap.UMAP(
            n_components=2,
            n_neighbors=min(lcfg["umap_2d_neighbors"], len(ids) - 1),
            min_dist=lcfg["umap_2d_min_dist"],
            metric="cosine",
            random_state=seed,
        ).fit_transform(centroids)
    else:
        ang = np.linspace(0, 2 * np.pi, len(ids), endpoint=False)
        pos = np.stack([np.cos(ang), np.sin(ang)], axis=1)

    # scale into view box with margins
    W, H = float(lcfg["view_w"]), float(lcfg["view_h"])
    margin = 90.0
    for ax in range(2):
        lo, hi = pos[:, ax].min(), pos[:, ax].max()
        span = max(hi - lo, 1e-6)
        pos[:, ax] = (pos[:, ax] - lo) / span
    pos[:, 0] = margin + pos[:, 0] * (W - 2 * margin)
    pos[:, 1] = margin + pos[:, 1] * (H - 2 * margin)

    size = info.loc[ids, "size"].to_numpy(dtype=float)
    r = np.sqrt(size)
    r = 8 + (r / r.max()) * 42  # fine topic radius 8–50

    rows = []
    for i, tid in enumerate(ids):
        rows.append({
            "kind": "topic", "id": int(tid),
            "x": round(float(pos[i, 0]), 1), "y": round(float(pos[i, 1]), 1),
            "r": round(float(r[i]), 1),
            "parent": int(info.loc[tid, "coarse_topic"]),
        })
    fine_df = pd.DataFrame(rows)

    # --- coarse hubs ---
    hub_rows = []
    for cid, grp in fine_df.groupby("parent"):
        sizes = info.loc[grp["id"], "size"].to_numpy(dtype=float)
        hx = float(np.average(grp["x"], weights=sizes))
        hy = float(np.average(grp["y"], weights=sizes))
        hub_rows.append({"kind": "group", "id": int(cid), "x": round(hx, 1), "y": round(hy, 1),
                         "r": 0.0, "parent": -1, "_size": sizes.sum()})
    hubs = pd.DataFrame(hub_rows)
    hr = np.sqrt(hubs["_size"].to_numpy(dtype=float))
    hubs["r"] = np.round(20 + (hr / hr.max()) * 70, 1)  # group hub radius 20–90
    hubs = hubs.drop(columns=["_size"])

    out = pd.concat([hubs, fine_df], ignore_index=True)

    # --- edges (cosine similarity between fine centroids) ---
    thr = float(lcfg["edge_similarity_threshold"])
    maxe = int(lcfg["max_edges_per_node"])
    sim = centroids @ centroids.T
    np.fill_diagonal(sim, -1)
    edges = []
    for i, tid in enumerate(ids):
        order = np.argsort(-sim[i])
        kept = 0
        for j in order:
            if sim[i, j] < thr or kept >= maxe:
                break
            if tid < ids[j]:  # undirected, write once
                edges.append({"s": int(tid), "t": int(ids[j]), "w": round(float(sim[i, j]), 3)})
                kept += 1
    pd.DataFrame(edges).to_parquet(work / "09_edges.parquet", index=False)
    write_table(out, work / "09_layout.parquet")
    print(f"[layout] {len(hubs)} hubs, {len(fine_df)} topics, {len(edges)} similarity edges")
    return out
