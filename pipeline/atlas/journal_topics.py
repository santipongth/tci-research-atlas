"""Journal × topic analytics for editors: topic mix, peers (D4), scope drift (D1), special-issue finder (D5).

Input everywhere: `jt` = one row per assigned, dated article (journal_key, topic_id ≥ 0, year).

topic_mix        a journal's topics in [start, end]: count and share of its articles
peer_journals    cosine similarity of topic-mix vectors between eligible journals (≥ journals.min_articles)
scope_drift      per year: Jensen–Shannon distance (base 2, 0 = same mix, 1 = disjoint) between that year's topic
                 mix and the pooled mix of the drift_reference_years before it; null when either side has
                 fewer than drift_min_articles articles
topic_shifts     topics whose share of the journal grew / shrank most from window B to window R (emerging windows)
special_issue    topics in special_issue_statuses hosted by ≤ max_hosts journals, where a host published
                 ≥ min_host_articles of the topic's articles in R
journal_opportunities  per journal, those topics "in_scope" (it published some of them in the window) or
                 "adjacent" (an edge of the map joins them to one of its scope_topics largest topics)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon


def in_years(jt: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    return jt[(jt["year"] >= start) & (jt["year"] <= end)]


def topic_mix(jt: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    """journal_key, topic_id, count, share (of the journal's assigned articles in [start, end])."""
    w = in_years(jt, start, end)
    c = w.groupby(["journal_key", "topic_id"]).size().rename("count").reset_index()
    c["share"] = c["count"] / c.groupby("journal_key")["count"].transform("sum")
    return c.sort_values(["journal_key", "count", "topic_id"], ascending=[True, False, True]).reset_index(drop=True)


def peer_journals(mix: pd.DataFrame, eligible: set[str], k: int, min_similarity: float
                  ) -> dict[str, list[tuple[str, float]]]:
    """{journal: [(peer, cosine)]} — the k most similar eligible journals with cosine ≥ min_similarity."""
    m = mix[mix["journal_key"].isin(eligible)]
    if m.empty or k == 0:
        return {}
    journals = sorted(m["journal_key"].unique())
    topics = sorted(m["topic_id"].unique())
    ji = {j: i for i, j in enumerate(journals)}
    ti = {t: i for i, t in enumerate(topics)}
    mat = np.zeros((len(journals), len(topics)))
    mat[m["journal_key"].map(ji).to_numpy(), m["topic_id"].map(ti).to_numpy()] = m["share"].to_numpy()
    norm = np.linalg.norm(mat, axis=1, keepdims=True)
    unit = mat / np.where(norm == 0, 1.0, norm)
    sim = np.round(unit @ unit.T, 4)             # ranked on the published precision: ties by name
    np.fill_diagonal(sim, -1.0)
    out = {}
    for i, j in enumerate(journals):
        order = np.lexsort((np.arange(len(journals)), -sim[i]))     # highest first, ties by name order
        peers = [(journals[o], float(sim[i, o])) for o in order[:k] if sim[i, o] >= min_similarity]
        out[j] = peers
    return out


def scope_drift(jt: pd.DataFrame, years: list[int], ref_years: int, min_articles: int) -> pd.DataFrame:
    """journal_key, year, articles, distance (NaN when not computable) for every journal-year in `years`."""
    if not years:
        return pd.DataFrame(columns=["journal_key", "year", "articles", "distance"])
    lo, hi = min(years) - ref_years, max(years)
    rows = []
    for jk, g in in_years(jt, lo, hi).groupby("journal_key"):    # the reference years before `years` count too
        tab = g.groupby(["year", "topic_id"]).size().unstack(fill_value=0).reindex(range(lo, hi + 1), fill_value=0)
        for y in years:
            cur = tab.loc[y].to_numpy(dtype=float)
            ref = tab.loc[y - ref_years:y - 1].sum().to_numpy(dtype=float)
            n = int(cur.sum())
            if n == 0:
                continue
            dist = (float(np.clip(jensenshannon(cur / cur.sum(), ref / ref.sum(), base=2), 0.0, 1.0))
                    if n >= min_articles and ref.sum() >= min_articles else np.nan)
            rows.append({"journal_key": jk, "year": int(y), "articles": n, "distance": dist})
    return pd.DataFrame(rows, columns=["journal_key", "year", "articles", "distance"])


def topic_shifts(jt: pd.DataFrame, before: tuple[int, int], after: tuple[int, int], n: int, min_articles: int
                 ) -> pd.DataFrame:
    """journal_key, topic_id, kind (gained | lost), share_before, share_after — the n largest share changes
    per journal, for journals with ≥ min_articles articles in both windows."""
    b, a = topic_mix(jt, *before), topic_mix(jt, *after)
    nb, na = b.groupby("journal_key")["count"].sum(), a.groupby("journal_key")["count"].sum()
    ok = set(nb[nb >= min_articles].index) & set(na[na >= min_articles].index)
    both = (b[b["journal_key"].isin(ok)][["journal_key", "topic_id", "share"]].rename(columns={"share": "share_before"})
            .merge(a[a["journal_key"].isin(ok)][["journal_key", "topic_id", "share"]]
                   .rename(columns={"share": "share_after"}), on=["journal_key", "topic_id"], how="outer")
            .fillna({"share_before": 0.0, "share_after": 0.0}))
    both["delta"] = both["share_after"] - both["share_before"]
    rows = []
    for _jk, g in both.groupby("journal_key"):
        up = g[g["delta"] > 0].sort_values(["delta", "topic_id"], ascending=[False, True]).head(n)
        down = g[g["delta"] < 0].sort_values(["delta", "topic_id"], ascending=[True, True]).head(n)
        rows += [up.assign(kind="gained"), down.assign(kind="lost")]
    cols = ["journal_key", "topic_id", "kind", "share_before", "share_after"]
    return pd.concat(rows, ignore_index=True)[cols] if rows else pd.DataFrame(columns=cols)


def special_issue(jt_recent: pd.DataFrame, status: pd.Series, statuses: list[str], min_host_articles: int,
                  max_hosts: int) -> pd.DataFrame:
    """topic_id, hosts, top_host_share, articles_R — topics of `statuses` with ≤ max_hosts host journals.
    jt_recent: the articles of window R; status: topic_id → status."""
    want = set(status[status.isin(statuses)].index)
    c = jt_recent[jt_recent["topic_id"].isin(want)].groupby(["topic_id", "journal_key"]).size().rename("n")
    present = set(c.index.get_level_values(0))
    rows = []
    for tid in sorted(want):
        per = c.loc[tid] if tid in present else pd.Series(dtype=int)
        total = int(per.sum())
        hosts = int((per >= min_host_articles).sum())
        if total == 0 or hosts > max_hosts:
            continue
        rows.append({"topic_id": int(tid), "hosts": hosts, "top_host_share": float(per.max() / total),
                     "articles_R": total})
    return pd.DataFrame(rows, columns=["topic_id", "hosts", "top_host_share", "articles_R"])


def journal_opportunities(opps: pd.DataFrame, mix: pd.DataFrame, edges: pd.DataFrame, scope_topics: int,
                          per_journal: int) -> pd.DataFrame:
    """journal_key, topic_id, reason (in_scope | adjacent), journal_articles, hosts — at most per_journal rows per
    journal: in_scope first (most of the journal's articles first), then adjacent; ties by fewer hosts, topic id."""
    cols = ["journal_key", "topic_id", "reason", "journal_articles", "hosts"]
    if opps.empty or mix.empty or per_journal == 0:
        return pd.DataFrame(columns=cols)
    hosts = opps.set_index("topic_id")["hosts"].to_dict()
    nbrs: dict[int, set[int]] = {}
    for s, t in zip(edges["s"].astype(int), edges["t"].astype(int)) if len(edges) else []:
        nbrs.setdefault(s, set()).add(t)
        nbrs.setdefault(t, set()).add(s)
    rows = []
    for jk, g in mix.groupby("journal_key"):
        have = dict(zip(g["topic_id"].astype(int), g["count"].astype(int)))
        top = g.sort_values(["count", "topic_id"], ascending=[False, True])["topic_id"].astype(int).head(scope_topics)
        near = set().union(*(nbrs.get(t, set()) for t in top)) if len(top) else set()
        found = []
        for tid in hosts:
            if tid in have:
                found.append((0, -have[tid], hosts[tid], tid, "in_scope", have[tid]))
            elif tid in near:
                found.append((1, 0, hosts[tid], tid, "adjacent", 0))
        for *_, tid, reason, n in sorted(found)[:per_journal]:
            rows.append({"journal_key": jk, "topic_id": int(tid), "reason": reason, "journal_articles": int(n),
                         "hosts": int(hosts[tid])})
    return pd.DataFrame(rows, columns=cols)
