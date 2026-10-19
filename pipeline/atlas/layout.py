"""2D layout of topics for the atlas map (+ article "galaxy"), stable across releases.

Positions: UMAP 2D on topic centroids (near = semantically similar). With layout.stable and a layout
from the previous release (state_dir/releases/<prev>/layout.parquet):
  1. UMAP starts from the previous positions (new topics: mean of their `init_neighbors` most similar
     continuing topics);
  2. the result is aligned to the previous positions by a similarity Procrustes fit on the continuing
     topics (no rotation, flip or zoom between quarters);
  3. continuing topics end at anchor·previous + (1 − anchor)·aligned; a new topic gets the mean shift of
     its nearest continuing neighbours, so it lands next to them on the anchored map.
Without a previous layout (first release, or < 3 continuing topics): min-max scaling into the view box.
Group hubs sit at the size-weighted mean of their topics. Edges = centroid cosine ≥ threshold.

Galaxy: every assigned article is placed inside its topic's circle — angle from the topic's first two
principal components (sign-fixed), radius from the rank of its distance to the centroid (uniform disc).
Same inputs → same coordinates.

Outputs: work/09_layout (kind, id, x, y, r, parent), work/09_edges (s, t, w), work/09_galaxy
(article_id, topic_id, gx, gy); state_dir/releases/<release>/layout.parquet (topic_id, x, y).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.checkpoints import load_aligned
from atlas.io_utils import read_table, write_table
from atlas.state import previous_release, release_dir
from atlas.taxonomy import load_topic_groups


def procrustes_fit(A: np.ndarray, B: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """Similarity transform (scale s, orthogonal R, shift t) with s·A·R + t ≈ B (least squares)."""
    ma, mb = A.mean(axis=0), B.mean(axis=0)
    A0, B0 = A - ma, B - mb
    U, S, Vt = np.linalg.svd(A0.T @ B0)
    R = U @ Vt
    s = float(S.sum() / max((A0 ** 2).sum(), 1e-12))
    return s, R, mb - s * ma @ R


def _minmax_to_view(pos: np.ndarray, W: float, H: float, margin: float) -> np.ndarray:
    out = pos.astype(float).copy()
    for ax, size in ((0, W), (1, H)):
        lo, hi = out[:, ax].min(), out[:, ax].max()
        out[:, ax] = margin + (out[:, ax] - lo) / max(hi - lo, 1e-6) * (size - 2 * margin)
    return out


def init_positions(ids: list[int], C: np.ndarray, prev_xy: dict[int, tuple[float, float]],
                   k: int) -> np.ndarray | None:
    """UMAP init (~10-unit scale): previous positions for continuing topics, neighbour mean for new ones."""
    keep = [i for i, t in enumerate(ids) if t in prev_xy]
    if len(keep) < 3:
        return None
    P = np.array([prev_xy[ids[i]] for i in keep], dtype=float)
    lo, span = P.min(axis=0), np.maximum(np.ptp(P, axis=0), 1e-6)
    init = np.zeros((len(ids), 2))
    init[keep] = 10.0 * (P - lo) / span
    sims = C @ C[keep].T
    for i in range(len(ids)):
        if ids[i] not in prev_xy:
            nn = np.argsort(-sims[i])[:k]
            init[i] = init[np.array(keep)[nn]].mean(axis=0)
    jitter = np.random.default_rng(0).normal(0, 1e-3, init.shape)        # UMAP needs distinct starting points
    return (init + jitter).astype(np.float32)


def topic_positions(ids: list[int], C: np.ndarray, lcfg: dict, seed: int,
                    prev_xy: dict[int, tuple[float, float]]) -> np.ndarray:
    W, H = float(lcfg["view_w"]), float(lcfg["view_h"])
    margin = float(lcfg["margin"])
    init = init_positions(ids, C, prev_xy, int(lcfg["init_neighbors"])) if lcfg["stable"] and prev_xy else None
    if len(ids) >= 4:
        import umap

        pos = umap.UMAP(n_components=2, n_neighbors=min(int(lcfg["umap_2d_neighbors"]), len(ids) - 1),
                        min_dist=float(lcfg["umap_2d_min_dist"]), metric="cosine", random_state=seed,
                        init=init if init is not None else "spectral").fit_transform(C)
    else:
        ang = np.linspace(0, 2 * np.pi, len(ids), endpoint=False)
        pos = np.stack([np.cos(ang), np.sin(ang)], axis=1)
    keep = [i for i, t in enumerate(ids) if t in prev_xy]
    if init is None or len(keep) < 3:
        return _minmax_to_view(pos, W, H, margin)
    P = np.array([prev_xy[ids[i]] for i in keep], dtype=float)
    s, R, t = procrustes_fit(pos[keep], P)
    aligned = s * pos @ R + t
    a = float(lcfg["anchor"])
    out = aligned.copy()
    out[keep] = a * P + (1 - a) * aligned[keep]             # continuing topics stay (almost) where they were
    shift = out[keep] - aligned[keep]
    sims = C @ C[keep].T
    for i in range(len(ids)):                                # a new topic moves with its nearest old neighbours
        if ids[i] not in prev_xy:
            out[i] = aligned[i] + shift[np.argsort(-sims[i])[:int(lcfg["init_neighbors"])]].mean(axis=0)
    out[:, 0] = np.clip(out[:, 0], margin, W - margin)
    out[:, 1] = np.clip(out[:, 1], margin, H - margin)
    return out


def galaxy_coords(member_emb: np.ndarray, centroid: np.ndarray, cx: float, cy: float,
                  radius: float) -> tuple[np.ndarray, np.ndarray]:
    n = len(member_emb)
    if n == 1:
        return np.array([cx]), np.array([cy])
    X = member_emb - member_emb.mean(axis=0)
    _, _, Vt = np.linalg.svd(X, full_matrices=False)
    comps = Vt[:2].copy()
    for c in comps:                                       # sign convention → deterministic orientation
        if c[np.argmax(np.abs(c))] < 0:
            c *= -1
    P = X @ comps.T
    if P.shape[1] == 1:
        P = np.hstack([P, np.zeros((n, 1))])
    angle = np.arctan2(P[:, 1], P[:, 0])
    dist = 1.0 - member_emb @ centroid
    rank = np.argsort(np.argsort(dist, kind="stable"), kind="stable")
    rr = 0.95 * radius * np.sqrt((rank + 0.5) / n)
    return cx + rr * np.cos(angle), cy + rr * np.sin(angle)


def layout(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    lcfg = cfg["layout"]
    seed = int(cfg["pipeline"]["seed"])
    C = np.load(work / "04_centroids.npy")
    ids = [int(t) for t in json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))]
    info = read_table(work / "04_topic_info.parquet").set_index("topic_id")
    group_of = load_topic_groups(work).set_index("topic_id")["group_id"].to_dict()

    prev_rel = previous_release(cfg)
    prev_xy: dict[int, tuple[float, float]] = {}
    if prev_rel and (release_dir(cfg, prev_rel) / "layout.parquet").exists():
        p = read_table(release_dir(cfg, prev_rel) / "layout.parquet")
        prev_xy = {int(r.topic_id): (float(r.x), float(r.y)) for r in p.itertuples()}
    pos = topic_positions(ids, C, lcfg, seed, prev_xy)

    size = info.loc[ids, "size"].to_numpy(dtype=float)
    r = 8 + (np.sqrt(size) / np.sqrt(size).max()) * 42          # fine topic radius 8–50
    fine_df = pd.DataFrame([{"kind": "topic", "id": tid, "x": round(float(pos[i, 0]), 1),
                             "y": round(float(pos[i, 1]), 1), "r": round(float(r[i]), 1),
                             "parent": int(group_of.get(tid, info.loc[tid, "coarse_topic"]))}
                            for i, tid in enumerate(ids)])
    hub_rows = []
    for gid, grp in fine_df.groupby("parent"):
        sizes = info.loc[grp["id"], "size"].to_numpy(dtype=float)
        hub_rows.append({"kind": "group", "id": int(gid), "x": round(float(np.average(grp["x"], weights=sizes)), 1),
                         "y": round(float(np.average(grp["y"], weights=sizes)), 1), "r": 0.0, "parent": -1,
                         "_size": sizes.sum()})
    hubs = pd.DataFrame(hub_rows)
    hr = np.sqrt(hubs["_size"].to_numpy(dtype=float))
    hubs["r"] = np.round(20 + (hr / hr.max()) * 70, 1)             # group hub radius 20–90
    out = pd.concat([hubs.drop(columns=["_size"]), fine_df], ignore_index=True)

    thr, maxe = float(lcfg["edge_similarity_threshold"]), int(lcfg["max_edges_per_node"])
    sim = C @ C.T
    np.fill_diagonal(sim, -1)
    edges = []
    for i, tid in enumerate(ids):
        kept = 0
        for j in np.argsort(-sim[i]):
            if sim[i, j] < thr or kept >= maxe:
                break
            if tid < ids[j]:                                          # undirected, write once
                edges.append({"s": tid, "t": ids[j], "w": round(float(sim[i, j]), 3)})
                kept += 1

    if lcfg["galaxy"]:
        docs, emb = load_aligned(work)
        fine = docs[["article_id"]].merge(read_table(work / "04_fine_topics.parquet"), on="article_id", how="left")
        labels = fine["fine_topic"].fillna(-1).astype(int).to_numpy()
        parts = []
        for i, tid in enumerate(ids):
            members = np.where(labels == tid)[0]
            if len(members):
                gx, gy = galaxy_coords(emb[members], C[i], float(pos[i, 0]), float(pos[i, 1]), float(r[i]))
                parts.append(pd.DataFrame({"article_id": fine["article_id"].to_numpy()[members], "topic_id": tid,
                                           "gx": np.round(gx, 2), "gy": np.round(gy, 2)}))
        galaxy = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
            columns=["article_id", "topic_id", "gx", "gy"])
        write_table(galaxy, work / "09_galaxy.parquet")

    write_table(pd.DataFrame(edges, columns=["s", "t", "w"]), work / "09_edges.parquet")
    write_table(out, work / "09_layout.parquet")
    write_table(fine_df[["id", "x", "y"]].rename(columns={"id": "topic_id"}),
                release_dir(cfg, create=True) / "layout.parquet")
    moved = ""
    if prev_xy:
        cont = [i for i, t in enumerate(ids) if t in prev_xy]
        if cont:
            d = np.hypot(*(pos[cont] - np.array([prev_xy[ids[i]] for i in cont])).T)
            moved = f", continuing topics moved {np.median(d):.0f}px (median)"
    print(f"[layout] {len(hubs)} hubs, {len(fine_df)} topics, {len(edges)} similarity edges{moved}")
    return out
