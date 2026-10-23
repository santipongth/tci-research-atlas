"""Step `gaps` (after benchmark): the gap finder (R5) and concentration risk (E10) → work/18_* (export: gaps.json).

Articles of the emerging recent window R; institutions from 15_article_institutions, journals from the corpus.
  18_gap_few_institutions  topic_id, status, institutions — topics in gaps.statuses studied by ≤ gaps.max_institutions
                           institutions in R (topics flagged orgs_unverified are left out: too little affiliation data
                           for "few institutions" to mean anything)
  18_gap_bridges           s, t, similarity, shared, jaccard — map neighbours (09_edges w ≥ bridge_min_similarity)
                           whose institution sets in R barely overlap (Jaccard ≤ bridge_max_jaccard)
  18_gap_world             subfield_id, subfield_en, world_ratio, activity_index, topics ("3;7") — benchmark
                           opportunities with the corpus topics anchored there (none without 17_benchmark)
  18_concentration         scope (topic | group), unit (topic id | group id), kind (institution | journal), articles,
                           hhi, top_share, top_key, concentrated — units with ≥ risk.min_articles articles in R (articles
                           with ≥ 1 known institution for kind=institution); HHI = Σ p² over the items' article counts;
                           top_share = articles with the largest item ÷ the unit's articles; concentrated =
                           top_share ≥ risk.max_top_share or hhi ≥ risk.max_hhi
  18_gaps_meta.json        {"R": [first, last]}
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from atlas.io_utils import read_or_empty, read_table, write_table
from atlas.registry import journal_keys
from atlas.taxonomy import load_topic_groups

CONC_COLUMNS = ["scope", "unit", "kind", "articles", "hhi", "top_share", "top_key", "concentrated"]
WORLD_COLUMNS = ["subfield_id", "subfield_en", "world_ratio", "activity_index", "topics"]


def concentration(df: pd.DataFrame, unit: str, item: str) -> pd.DataFrame:
    """df: article_id, <unit>, <item> → <unit>, articles, hhi, top_share, top_key (one row per unit)."""
    cols = [unit, "articles", "hhi", "top_share", "top_key"]
    d = df[["article_id", unit, item]].drop_duplicates()
    if d.empty:
        return pd.DataFrame(columns=cols)
    arts = d.groupby(unit)["article_id"].nunique()
    n = d.groupby([unit, item]).size().rename("n").reset_index()
    n["p"] = n["n"] / n.groupby(unit)["n"].transform("sum")
    hhi = (n["p"] ** 2).groupby(n[unit]).sum()
    top = n.sort_values([unit, "n", item], ascending=[True, False, True]).drop_duplicates(unit).set_index(unit)
    return pd.DataFrame({unit: arts.index, "articles": arts.to_numpy(), "hhi": hhi.reindex(arts.index).to_numpy(),
                         "top_share": (top["n"].reindex(arts.index) / arts).to_numpy(),
                         "top_key": top[item].reindex(arts.index).to_numpy()}, columns=cols)


def few_institution_topics(status: pd.Series, n_inst: pd.Series, statuses: Iterable[str], max_n: int) -> pd.Series:
    """{topic: institutions} for topics whose status is in `statuses` and with ≤ max_n institutions (missing = 0)."""
    s = status[status.isin(list(statuses))]
    n = n_inst.reindex(s.index).fillna(0).astype(int)
    return n[n <= max_n].sort_values(kind="stable")


def weak_bridges(edges: pd.DataFrame, inst_sets: dict[int, set], min_sim: float, max_jaccard: float,
                 limit: int) -> pd.DataFrame:
    cols = ["s", "t", "similarity", "shared", "jaccard"]
    rows = []
    for e in edges.itertuples():
        if float(e.w) < min_sim:
            continue
        a, b = inst_sets.get(int(e.s), set()), inst_sets.get(int(e.t), set())
        if not a or not b:
            continue
        shared = len(a & b)
        j = shared / len(a | b)
        if j <= max_jaccard:
            rows.append({"s": int(e.s), "t": int(e.t), "similarity": round(float(e.w), 4), "shared": shared,
                         "jaccard": round(j, 4)})
    out = pd.DataFrame(rows, columns=cols)
    return out.sort_values(["similarity", "s", "t"], ascending=[False, True, True]).head(limit).reset_index(drop=True)


def world_gaps(work: Path, limit: int) -> pd.DataFrame:
    bench = read_or_empty(work / "17_benchmark.parquet", [])
    tax = read_or_empty(work / "10_taxonomy.parquet", ["topic_id", "subfield_id"])
    if bench.empty:
        return pd.DataFrame(columns=WORLD_COLUMNS)
    anchored = (tax.astype({"subfield_id": str}).groupby("subfield_id")["topic_id"]
                .agg(lambda s: ";".join(str(int(t)) for t in sorted(s))))
    opp = bench[bench["opportunity"].fillna(False).astype(bool)].astype({"subfield_id": str})
    out = opp.assign(topics=opp["subfield_id"].map(anchored).fillna(""))
    return out.sort_values(["world_ratio", "subfield_id"], ascending=[False, True]).head(limit)[WORLD_COLUMNS]


def gaps(cfg: dict) -> dict:
    work = Path(cfg["pipeline"]["work_dir"])
    gcfg, rcfg = cfg["gaps"], cfg["risk"]
    for stale in work.glob("18_*"):
        stale.unlink()
    last = int(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["last_complete_year"])
    R = (last - int(cfg["emerging"]["recent_window"]) + 1, last)
    limit = int(gcfg["max_items"])

    arts = read_table(work / "01_articles.parquet", ["article_id", "journal_name", "journal_key", "year"])
    arts = arts.assign(journal_key=journal_keys(arts), year=pd.to_numeric(arts["year"], errors="coerce"))
    in_r = arts[arts["year"].between(*R).fillna(False).astype(bool)]
    docs = read_table(work / "02_docs.parquet", ["article_id"])
    fine = read_table(work / "04_fine_topics.parquet")[["article_id", "fine_topic"]]
    topic_of = docs.merge(fine, on="article_id").rename(columns={"fine_topic": "topic_id"})
    topic_of = topic_of[topic_of["topic_id"].fillna(-1).astype(int) >= 0].astype({"topic_id": int})
    ar = in_r[["article_id", "journal_key"]].merge(topic_of, on="article_id")
    links = read_or_empty(work / "15_article_institutions.parquet", ["article_id", "inst_key"])
    ai = ar.merge(links, on="article_id")

    # R5: emerging topics few institutions work on
    em = read_table(work / "07_emerging.parquet").set_index("topic_id")
    unverified = (em["orgs_unverified"].fillna(False).astype(bool) if "orgs_unverified" in em.columns
                  else pd.Series(False, index=em.index))
    n_inst = ai.groupby("topic_id")["inst_key"].nunique()
    few = few_institution_topics(em.loc[~unverified, "status"], n_inst, gcfg["statuses"],
                                 int(gcfg["max_institutions"])).head(limit)
    few_df = pd.DataFrame({"topic_id": few.index.astype(int), "status": em.loc[few.index, "status"].to_numpy(),
                           "institutions": few.to_numpy(dtype=int)})

    # R5: neighbouring topics whose communities barely meet; world opportunities
    edges = read_or_empty(work / "09_edges.parquet", ["s", "t", "w"])
    sets = {int(t): set(g) for t, g in ai.groupby("topic_id")["inst_key"]}
    bridges = weak_bridges(edges, sets, float(gcfg["bridge_min_similarity"]), float(gcfg["bridge_max_jaccard"]), limit)
    world = world_gaps(work, limit)

    # E10: concentration per topic and per field, by institution and by journal
    sources = (("institution", ai[["article_id", "topic_id", "inst_key"]], "inst_key"),
               ("journal", ar[ar["journal_key"] != ""][["article_id", "topic_id", "journal_key"]], "journal_key"))
    try:
        groups = load_topic_groups(work)[["topic_id", "group_id"]]
    except FileNotFoundError:
        groups = None
    parts = []
    for kind, df, item in sources:
        parts.append(concentration(df, "topic_id", item).rename(columns={"topic_id": "unit"})
                     .assign(scope="topic", kind=kind))
        if groups is not None:
            parts.append(concentration(df.merge(groups, on="topic_id"), "group_id", item)
                         .rename(columns={"group_id": "unit"}).assign(scope="group", kind=kind))
    parts = [p for p in parts if len(p)]
    conc = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=CONC_COLUMNS)
    conc = conc[conc["articles"] >= int(rcfg["min_articles"])].copy()
    conc["concentrated"] = ((conc["top_share"] >= float(rcfg["max_top_share"]))
                            | (conc["hhi"] >= float(rcfg["max_hhi"]))).astype(bool)
    conc = conc.astype({"unit": int, "articles": int}).sort_values(
        ["concentrated", "top_share", "scope", "unit", "kind"], ascending=[False, False, True, True, True])

    write_table(few_df, work / "18_gap_few_institutions.parquet")
    write_table(bridges, work / "18_gap_bridges.parquet")
    write_table(world.reset_index(drop=True), work / "18_gap_world.parquet")
    write_table(conc[CONC_COLUMNS].reset_index(drop=True), work / "18_concentration.parquet")
    meta = {"R": list(R)}
    (work / "18_gaps_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    print(f"[gaps] {len(few_df)} thin emerging topics, {len(bridges)} weak bridges, {len(world)} world opportunities, "
          f"{int(conc['concentrated'].sum())} concentrated units")
    return meta
