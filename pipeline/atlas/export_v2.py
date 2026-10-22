"""Export data contract v2 → output_dir/data/<release>/ (+ output_dir/data/latest.json).

Every file is built as a pydantic model from atlas/schema/contract.py (validation happens on
construction; NaN/Infinity are rejected) and written as compact strict JSON. manifest.json lists
every other file with its byte size and sha256, the interval level (ci_level), the v3 data-quality
fields and the label/LLM accounting. Representative articles carry titles and links back to ThaiJO
only — abstracts are never published (journal copyright). Institutions are counted at organisation
level (org_key) and published under their most frequent written name (atlas.orgs.org_display_names —
tone marks and case kept); no person is ranked (PDPA). A topic or keyword with no baseline articles is published with
share_ratio null and no_baseline true (the web says "new — no baseline").
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
from datetime import UTC
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.checkpoints import load_aligned
from atlas.diff import load_snapshot, make_snapshot, quarter_diff, write_snapshot
from atlas.export import _git_hash, fine_labels
from atlas.export_editors import journal_files, match_file, methods_file
from atlas.export_exec import (
    executive_summary,
    gaps_file,
    global_file,
    institution_files,
    regions_file,
    sdg_file,
    skipped_modules,
    topic_institutions,
    topic_sdg_numbers,
)
from atlas.export_research import references_file, search_files, topic_citations
from atlas.io_utils import read_table
from atlas.label import representative_indices
from atlas.lineage import topic_code
from atlas.llm_runner import release_spend
from atlas.orgs import org_display_names
from atlas.registry import journal_keys, journal_path
from atlas.schema import contract as C
from atlas.state import is_newest, known_releases, previous_release, release_dir, snapshot_at, work_release
from atlas.taxonomy import FALLBACK_GROUP_BASE, load_topic_groups

N_COLOR_TOKENS = 12
# Map colours follow the group id, never its size rank, so a group keeps its colour across quarters.
# OpenAlex fields (Scopus ASJC ids 11–36) → fixed tokens: the 12 fields most common in TCI journals get distinct
# tokens; the other 14 share tokens with fields of another domain. Agglomerative / fallback groups G<n> → n mod 12.
# Two groups of one release that want the same token: the lower id keeps it, the other takes the next free token
# (group_colors) — decided by the set of ids only, never by size.
FIELD_COLOR = {"33": 1, "14": 2, "12": 3, "27": 4, "11": 5, "32": 6, "20": 7, "22": 8, "17": 9, "29": 10, "23": 11,
               "36": 12, "13": 1, "15": 2, "16": 3, "18": 4, "19": 5, "21": 6, "24": 7, "25": 10, "26": 12, "28": 8,
               "30": 11, "31": 4, "34": 9, "35": 6}


def _f(v, nd: int = 4) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if math.isfinite(x) else None


def _json_list(s) -> list:
    return json.loads(s) if isinstance(s, str) and s else []


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _optional(path: Path) -> pd.DataFrame | None:
    try:
        return read_table(path)
    except FileNotFoundError:
        return None


def config_hash(cfg: dict) -> str:
    """Hash of every setting that can change results (paths and the release name excluded)."""
    body = {k: v for k, v in cfg.items() if k != "pipeline"}
    body["pipeline"] = {k: v for k, v in cfg["pipeline"].items() if k in ("seed",)}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]


def group_code(gid: int, source: str) -> str:
    """F<field> for an OpenAlex field, G<coarse> for an agglomerative group — also for the fallback groups
    (id FALLBACK_GROUP_BASE + coarse) that topics unknown to a stale 10_taxonomy get, so never an F code."""
    gid = int(gid)
    if gid >= FALLBACK_GROUP_BASE:
        return f"G{gid - FALLBACK_GROUP_BASE:02d}"
    return f"{'F' if source == 'openalex' else 'G'}{gid:02d}"


def group_color(code: str) -> str:
    """Design token of a published group code (F<field> | G<n>) — a fixed function of the id."""
    n = int(code[1:])
    k = FIELD_COLOR.get(str(n), n % N_COLOR_TOKENS + 1) if code.startswith("F") else n % N_COLOR_TOKENS + 1
    return f"cat-{k:02d}"


def group_colors(codes) -> dict[str, str]:
    """{group code: token} for one release: group_color, with collisions moved to the next free token (≤ 12 groups
    never share a colour; beyond 12 the extra groups keep their preferred token)."""
    out, used = {}, set()
    for code in sorted(set(codes), key=lambda c: (c[0] != "F", int(c[1:]))):
        want = int(group_color(code)[4:])
        free = [t for t in ((want - 1 + i) % N_COLOR_TOKENS + 1 for i in range(N_COLOR_TOKENS)) if t not in used]
        tok = free[0] if free else want
        used.add(tok)
        out[code] = f"cat-{tok:02d}"
    return out


def _metrics(e: pd.Series, min_recent: int) -> C.TopicMetrics:
    no_base = float(e["share_baseline"]) == 0.0
    reason = None
    if str(e["status"]) == "LOW_DATA":
        reason = "few_articles" if int(e["count_recent"]) < min_recent else "not_estimable"
    return C.TopicMetrics(
        count_recent=int(e["count_recent"]), share_recent=_f(e["share_recent"], 6) or 0.0,
        share_baseline=_f(e["share_baseline"], 6) or 0.0,
        share_ratio=None if no_base else (_f(e["share_ratio"]) or 0.0), no_baseline=no_base,
        share_growth=_f(e["share_growth"]), share_growth_lo=_f(e["share_growth_lo"]),
        share_growth_hi=_f(e["share_growth_hi"]), acceleration=_f(e["acceleration"]) or 0.0,
        burst_frac=_f(e["burst_frac"]) or 0.0,
        burst_years=[int(y) for y in str(e["burst_years"] or "").split(",") if y.strip()],
        novelty=_f(e["novelty"]) or 0.0, coherence=_f(e["coherence"]), n_journals_R=int(e["n_journals_R"]),
        n_orgs_R=int(e["n_orgs_R"]), new_journal_share=_f(e["new_journal_share"]) or 0.0,
        journal_hhi=_f(e["journal_hhi"]) or 0.0, journal_driven=bool(e["journal_driven"]),
        orgs_unverified=bool(e.get("orgs_unverified", False)), low_data_reason=reason)


def _forecast(f: pd.Series) -> C.TopicForecast:
    show = bool(f["show"]) if pd.notna(f["show"]) else False
    lists = {k: [float(v) for v in _json_list(f[c])] if show else []
             for k, c in (("mean", "fc_mean"), ("lo80", "fc_lo80"), ("hi80", "fc_hi80"),
                          ("lo95", "fc_lo95"), ("hi95", "fc_hi95"))}
    return C.TopicForecast(model=str(f["model"]), mase=_f(f["mase"], 3), skill_vs_naive=_f(f["skill_vs_naive"], 3) or 0.0,
                           show=show, years=[int(y) for y in _json_list(f["fc_years"])] if show else [], **lists)


def build_release(cfg: dict) -> dict[str, C._Model]:
    """{published relative path: model} for one release (nothing is written)."""
    work = Path(cfg["pipeline"]["work_dir"])
    ecfg = cfg["export"]
    release = work_release(cfg)                    # the release work_dir was clustered for (ReleaseMismatch otherwise)
    prev = previous_release(cfg, release)
    now = snapshot_at(cfg).astimezone(UTC).isoformat()   # recorded snapshot: re-exports are byte-identical
    docs, emb = load_aligned(work)
    info = read_table(work / "04_topic_info.parquet")
    labels = fine_labels(read_table(work / "05_labels.parquet")).set_index("topic_id")
    em = read_table(work / "07_emerging.parquet").set_index("topic_id")
    fc = read_table(work / "08_forecasts.parquet").set_index("topic_id")
    lay = read_table(work / "09_layout.parquet")
    edges = read_table(work / "09_edges.parquet")
    fine = docs[["article_id"]].merge(read_table(work / "04_fine_topics.parquet"), on="article_id", how="left")
    labels_arr = fine["fine_topic"].fillna(-1).astype(int).to_numpy()
    meta6 = _read_json(work / "06_meta.json")
    fmeta = _read_json(work / "08_forecast_meta.json")
    taxmeta = _read_json(work / "10_taxonomy_meta.json")
    tax = _optional(work / "10_taxonomy.parquet")
    source = "openalex" if tax is not None and len(tax) and (tax["source"] == "openalex").all() else "agglomerative"
    groups = load_topic_groups(work).set_index("topic_id")
    lineage = _optional(work / "04_lineage.parquet")
    lin = lineage.set_index("topic_id") if lineage is not None and len(lineage) else pd.DataFrame()
    reg_path = release_dir(cfg, release) / "topics" / "registry.parquet"
    born = read_table(reg_path).set_index("topic_id")["born"].to_dict() if reg_path.exists() else {}
    galaxy = _optional(work / "09_galaxy.parquet")
    gxy = galaxy.set_index("article_id")[["gx", "gy"]] if galaxy is not None and len(galaxy) else None
    try:
        authors = read_table(work / "01_authors.parquet")
    except FileNotFoundError:
        authors = pd.DataFrame(columns=["article_id", "org_key"])
    org_names = org_display_names(authors)                  # org_key counts; its written name is published
    orgs = authors.loc[authors["org_key"].astype(str) != "", ["article_id", "org_key"]].drop_duplicates()

    pos = lay[lay["kind"] == "topic"].set_index("id")
    hubs = lay[lay["kind"] == "group"].set_index("id")
    ids = [int(t) for t in info["topic_id"]]
    size_of = info.set_index("topic_id")["size"].to_dict()
    tax_i = tax.set_index("topic_id") if tax is not None and source == "openalex" else None
    code = {t: topic_code(t) for t in ids}
    cent_ids = json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))
    cents = dict(zip(cent_ids, np.load(work / "04_centroids.npy")))

    min_recent = int(cfg["emerging"]["min_articles_recent"])
    narr = _optional(work / "11_narratives.parquet")
    narratives = ({int(r.topic_id): C.Narrative(th=str(r.th), en=str(r.en), source=str(r.source))
                   for r in narr.itertuples()} if narr is not None else {})
    brief = _read_json(work / "11_brief.json")

    # ---- topics.json
    sdg_of = topic_sdg_numbers(work)                # P3: SDG numbers per topic (empty without the sdg step)
    topics = []
    for t in ids:
        e, g = em.loc[t] if t in em.index else None, groups.loc[t]
        f = fc.loc[t] if t in fc.index else None
        lb = labels.loc[t] if t in labels.index else None
        ev = lin.loc[t] if len(lin) and t in lin.index else None
        event = str(ev["event"]) if ev is not None and ev["event"] in ("new", "continue", "split", "merge") else "new"
        parents = [topic_code(int(p)) for p in str(ev["parents"] if ev is not None else "").split(";") if p]
        tx = tax_i.loc[t] if tax_i is not None and t in tax_i.index else None
        nowcast = None
        if f is not None and "nowcast_mean" in f and pd.notna(f["nowcast_mean"]):
            nowcast = C.TopicNowcast(year=int(f["nowcast_year"]), as_of_month=int(f["nowcast_month"]),
                                     ytd=int(f["nowcast_ytd"]), mean=float(f["nowcast_mean"]))
        topics.append(C.Topic(
            id=code[t], group=group_code(g["group_id"], source),
            th=str(lb["name_th"]) if lb is not None else code[t], en=str(lb["name_en"]) if lb is not None else code[t],
            description=str(lb["description"] or "") if lb is not None else "",
            keywords=[k for k in str(lb["keywords"] or "").split("; ") if k] if lb is not None else [],
            label_source=str(lb.get("label_source", "keywords")) if lb is not None else "keywords",
            size=int(size_of[t]),
            x=float(pos.loc[t, "x"]), y=float(pos.loc[t, "y"]), r=float(pos.loc[t, "r"]),
            status=str(e["status"]) if e is not None else "LOW_DATA",
            score=(_f(e["emerging_score"], 1) or 0.0) if e is not None else 0.0,
            metrics=_metrics(e, min_recent) if e is not None else C.TopicMetrics(
                count_recent=0, share_recent=0.0, share_baseline=0.0, share_ratio=None, share_growth=None,
                share_growth_lo=None, share_growth_hi=None, acceleration=0.0, burst_frac=0.0, novelty=0.0,
                n_journals_R=0, n_orgs_R=0, new_journal_share=0.0, journal_hhi=0.0, journal_driven=False,
                low_data_reason="few_articles"),
            forecast=_forecast(f) if f is not None else None,
            lineage=C.TopicLineage(born=born.get(t), event=event, parents=parents),
            subfield=str(tx["subfield_id"]) if tx is not None else None,
            subfield_en=str(tx["subfield_en"]) if tx is not None else "",
            cross_field=bool(tx["cross_field"]) if tx is not None else False,
            taxonomy_vote=_f(tx["vote_share"]) if tx is not None else None,
            sdg=sdg_of.get(t, []), nowcast=nowcast))
    files: dict[str, C._Model] = {"topics.json": C.TopicsFile(topics=topics)}

    # ---- editors' journal module (P2, optional) — before the topic details, which link journals by id
    topic_group = {t: group_code(groups.loc[t, "group_id"], source) for t in ids}
    editor_files, jid, jname = journal_files(cfg, work, code, topic_group)
    files.update(editor_files)
    jkey_of = pd.Series(journal_keys(docs).to_numpy(), index=docs["article_id"].to_numpy())

    # ---- executives' modules (P3, optional) — before the topic details, which link institutions by id
    exec_files, iid, inst_kpis = institution_files(cfg, work, code, topic_group)
    files.update(exec_files)
    gcode = lambda gid: group_code(gid, source)  # noqa: E731
    for name, model in (("regions.json", regions_file(cfg, work, iid)), ("sdg.json", sdg_file(cfg, work, code)),
                        ("global.json", global_file(cfg, work, code, gcode)),
                        ("gaps.json", gaps_file(cfg, work, code, iid, jid, jname, gcode))):
        if model is not None:
            files[name] = model

    # ---- researchers' modules (P4, optional)
    skipped = skipped_modules(cfg, work)
    refs_model, why = references_file(cfg, work, code, jid, jname)
    if refs_model is not None:
        files["references.json"] = refs_model
    elif why:
        skipped["references"] = why
    search_out, search_skipped = search_files(cfg, work, code)     # search/* + galaxy.json, aligned by doc ordinal
    files.update(search_out)
    skipped.update(search_skipped)
    cited_topic = topic_citations(work)        # None unless internal citation is published

    # ---- topics/<id>.json
    titles = docs.set_index("article_id")
    topic_of = pd.Series(labels_arr, index=docs["article_id"].to_numpy())
    oc = (orgs.assign(topic_id=orgs["article_id"].map(topic_of)).dropna(subset=["topic_id"])
          .astype({"topic_id": int}).query("topic_id >= 0")
          .groupby(["topic_id", "org_key"]).size().rename("count").reset_index()      # one groupby for all topics
          .sort_values(["topic_id", "count", "org_key"], ascending=[True, False, True])
          .groupby("topic_id").head(int(ecfg["max_topic_orgs"])))
    institutions = {int(t): [C.CountItem(key=org_names.get(k, k), count=int(n)) for k, n in zip(g["org_key"], g["count"])]
                    for t, g in oc.groupby("topic_id")}
    canonical = topic_institutions(work, docs["article_id"].to_numpy(), labels_arr, iid, int(ecfg["max_topic_orgs"]))
    if canonical is not None:                        # P3: canonical institutions (variants merged), linked when published
        institutions = canonical
    for t in ids:
        members = np.where(labels_arr == t)[0]
        idx = representative_indices(emb[members], cents[t], int(ecfg["repr_articles"]),
                                     float(cfg["labeling"]["mmr_lambda"])) if len(members) else []
        arts = []
        for aid in docs["article_id"].to_numpy()[members[idx]] if len(members) else []:
            row = titles.loc[aid]
            year = row.get("year")
            arts.append(C.RepresentativeArticle(
                article_id=str(aid), title=str(row.get("title", "") or ""), title_en=str(row.get("title_en", "") or ""),
                year=int(year) if pd.notna(year) else None, journal=str(row.get("journal_name", "") or ""),
                url=str(row.get("url", "") or ""), doi=str(row.get("doi", "") or ""),
                gx=_f(gxy.loc[aid, "gx"], 2) if gxy is not None and aid in gxy.index else None,
                gy=_f(gxy.loc[aid, "gy"], 2) if gxy is not None and aid in gxy.index else None))
        member_ids = docs["article_id"].to_numpy()[members]
        jc = jkey_of.loc[member_ids].value_counts().head(int(ecfg["max_topic_journals"]))
        nb = pd.concat([edges[edges["s"] == t].rename(columns={"t": "o"})[["o", "w"]],
                        edges[edges["t"] == t].rename(columns={"s": "o"})[["o", "w"]]])
        nb = nb.sort_values(["w", "o"], ascending=[False, True]).head(int(ecfg["max_neighbors"]))
        lb = labels.loc[t] if t in labels.index else None
        files[f"topics/{code[t]}.json"] = C.TopicDetail(
            id=code[t], articles=arts,
            journals=[C.CountItem(key=jname.get(k) or journal_path(k), count=int(v), id=jid.get(k))
                      for k, v in jc.items() if k],
            institutions=institutions.get(t, []),
            keywords=[k for k in str(lb["keywords"] or "").split("; ") if k] if lb is not None else [],
            neighbors=[code[int(o)] for o in nb["o"] if int(o) in code], narrative=narratives.get(t),
            cited_in_tci=cited_topic.get(t, (0, 0))[0] if cited_topic is not None else None)

    # ---- taxonomy.json (groups = map hubs)
    gsize = info.assign(g=info["topic_id"].map(groups["group_id"])).groupby("g")["size"].agg(["sum", "count"])
    order = gsize.sort_values("sum", ascending=False).index.tolist()
    names = groups.drop_duplicates("group_id").set_index("group_id")
    group_rows = []
    colors = group_colors(group_code(g, source) for g in order)
    for gid in order:
        th, en = str(names.loc[gid, "group_th"] or ""), str(names.loc[gid, "group_en"] or "")
        if not th or not en:                      # agglomerative fallback: name of its largest topic
            big = int(info[info["topic_id"].map(groups["group_id"]) == gid].sort_values("size").iloc[-1]["topic_id"])
            th = th or (str(labels.loc[big, "name_th"] or "") if big in labels.index else "") or code[big]
            en = en or (str(labels.loc[big, "name_en"] or "") if big in labels.index else "") or code[big]
        h = hubs.loc[gid] if gid in hubs.index else None
        gcode = group_code(gid, source)
        group_rows.append(C.GroupInfo(id=gcode, th=th, en=en, color=colors[gcode], size=int(gsize.loc[gid, "sum"]),
                                      n_topics=int(gsize.loc[gid, "count"]), x=float(h["x"]) if h is not None else 0.0,
                                      y=float(h["y"]) if h is not None else 0.0, r=float(h["r"]) if h is not None else 0.0))
    subfields = []
    if source == "openalex":
        tx = tax.merge(info[["topic_id", "size"]], on="topic_id")
        for sid, g in tx.groupby("subfield_id"):
            subfields.append(C.SubfieldInfo(id=str(sid), en=str(g["subfield_en"].iloc[0]),
                                            group=group_code(int(g["group_id"].iloc[0]), source),
                                            n_topics=int(len(g)), size=int(g["size"].sum())))
    files["taxonomy.json"] = C.TaxonomyFile(
        source=source, version=taxmeta.get("version"),
        holdout_accuracy_subfield=_f(taxmeta.get("holdout_accuracy_subfield")),
        holdout_accuracy_field=_f(taxmeta.get("holdout_accuracy_field")), groups=group_rows, subfields=subfields)

    # ---- series.json + edges.json + keywords.json
    s = read_table(work / "06_series.parquet")
    years = [int(y) for y in meta6.get("years", [])]
    files["series.json"] = C.SeriesFile(
        years=years, corpus_total=[int(meta6["totals"][str(y)]) for y in years],
        topics={code[int(t)]: g.set_index("year")["count"].reindex(years, fill_value=0).astype(int).tolist()
                for t, g in s.groupby("topic_id") if int(t) in code})
    files["edges.json"] = C.EdgesFile(edges=[C.Edge(s=code[int(r.s)], t=code[int(r.t)], w=float(r.w))
                                             for r in edges.itertuples() if int(r.s) in code and int(r.t) in code])
    kw = _optional(work / "07_keywords.parquet")
    if kw is not None:
        files["keywords.json"] = C.KeywordsFile(keywords=[
            C.EmergingKeyword(term=str(r.term), count_recent=int(r.count_recent),
                              share_ratio=None if bool(r.no_baseline) else (_f(r.share_ratio) or 0.0),
                              no_baseline=bool(r.no_baseline),
                              growth=_f(r.growth), growth_lo=_f(r.growth_lo), n_active_years=int(r.n_active_years),
                              n_orgs_R=int(r.n_orgs_R), n_journals_R=int(r.n_journals_R),
                              journal_driven=bool(r.journal_driven), emerging=bool(r.emerging),
                              topic=code.get(int(r.topic_id)))
            for r in kw.head(int(cfg["keywords"]["max_terms"])).itertuples()])

    # ---- overview.json
    nonempty = {c: docs[c].fillna("").astype(str).str.len() > 0 for c in ("abstract_en", "doi") if c in docs}
    kw_any = (docs.get("keywords_th", pd.Series("", index=docs.index)).fillna("").astype(str)
              + docs.get("keywords_en", pd.Series("", index=docs.index)).fillna("").astype(str)).str.len() > 0
    tq = pd.Series([f for v in docs.get("text_quality", pd.Series(dtype=str)).fillna("") for f in str(v).split("; ") if f])
    comp = meta6.get("completeness", {})
    nc = fmeta.get("nowcast")
    events = (lineage["event"].value_counts().to_dict() if lineage is not None else {})
    files["overview.json"] = C.Overview(
        release=release, previous_release=prev, generated_at=now, last_complete_year=int(meta6["last_complete_year"]),
        definition_version=int(cfg["emerging"]["definition_version"]),
        brief=C.Brief(**brief["brief"]) if brief.get("brief") else None, executive=executive_summary(files),
        kpis=C.Kpis(articles=len(docs), assigned_articles=int((labels_arr >= 0).sum()), topics=len(ids),
                    groups=len(group_rows), journals=int(docs["journal_name"].nunique()),
                    institutions=int(inst_kpis.get("institutions", orgs["org_key"].nunique())),
                    pct_international=inst_kpis.get("pct_international"),
                    pct_multi_institution=inst_kpis.get("pct_multi_institution"),
                    provinces=inst_kpis.get("provinces"),
                    pct_abstract_en=round(100 * float(nonempty["abstract_en"].mean()), 1) if "abstract_en" in nonempty else 0.0,
                    pct_doi=round(100 * float(nonempty["doi"].mean()), 1) if "doi" in nonempty else 0.0,
                    pct_keywords=round(100 * float(kw_any.mean()), 1) if len(docs) else 0.0),
        status_counts={str(k): int(v) for k, v in em["status"].value_counts().items()},
        corpus_by_year=[C.YearCount(year=y, articles=int(meta6["totals"][str(y)])) for y in years],
        corpus_forecast=[C.YearCount(year=int(y), articles=float(m))
                         for y, m in zip(fmeta.get("total_years", []), fmeta.get("total_mean", []))],
        nowcast=C.TopicNowcast(year=nc["year"], as_of_month=nc["as_of_month"], ytd=nc["ytd"], mean=nc["mean"]) if nc else None,
        lineage_events={str(k): int(v) for k, v in events.items()},
        retired_topics=[topic_code(int(r.topic_id)) for r in (lineage.itertuples() if lineage is not None else [])
                        if r.event == "retired"],
        data_quality=C.DataQuality(year_missing=int(docs["year"].isna().sum()),
                                   unassigned_articles=int((labels_arr < 0).sum()),
                                   completeness_method=str(comp.get("method", "median")),
                                   text_quality={str(k): int(v) for k, v in tq.value_counts().items()}))
    emb_meta = _read_json(work / "03_meta.json")
    modules = ["overview", "taxonomy", "topics", "topic_detail", "series", "edges"] + (["keywords"] if kw is not None else [])
    if editor_files:
        modules += ["journals", "journal_detail"]
    modules += [m for m in ("institutions", "regions", "sdg", "global", "gaps") if f"{m}.json" in files]
    if "institutions.json" in files:
        modules.append("institution_detail")
    modules += [m for m in ("references",) if f"{m}.json" in files]
    modules += [m for m, f in (("search", "search/meta.json"), ("galaxy", "galaxy.json")) if f in files]
    if (mf := methods_file(cfg, work, code)) is not None:
        files["methods.json"] = mf
        modules.append("methods")
    if (mx := match_file(work, code, jid)) is not None:
        files["match.json"] = mx
        modules.append("match")
    if prev and (diff := release_diff(cfg, release, prev, files)) is not None:
        files["diff.json"] = diff
        modules.append("diff")
    errs = _optional(work / "01_ingest_errors.parquet")
    files["manifest.json"] = C.Manifest(
        release=release, generated_at=now, pipeline_version=_git_hash(), config_hash=config_hash(cfg),
        definition_version=int(cfg["emerging"]["definition_version"]), ci_level=float(cfg["emerging"]["ci_level"]),
        as_of_year=meta6.get("as_of_year"), trimmed_years=[int(y) for y in meta6.get("trimmed_years", [])],
        embedding_provider=str(cfg["embedding"]["provider"]), embedding_model=str(emb_meta.get("model_id", "")),
        taxonomy_version=taxmeta.get("version"), modules=modules, previous_release=prev,
        n_orgs_unverified=int(em["orgs_unverified"].astype(bool).sum()) if "orgs_unverified" in em else 0,
        ingest_errors=len(errs) if errs is not None else None,          # unknown is never published as 0
        labels=_label_stats(cfg, labels), llm=_llm_stats(cfg, work, brief, release),
        skipped_modules=skipped)
    return files


def release_snapshot(release: str, files: dict[str, C._Model]) -> dict:
    """What the next release's diff compares with (atlas.diff)."""
    j = files.get("journals.json")
    return make_snapshot(release, [t.model_dump(mode="json") for t in files["topics.json"].topics],
                         files["overview.json"].kpis.model_dump(mode="json"),
                         [x.id for x in j.journals] if j is not None else None)


def release_diff(cfg: dict, release: str, prev: str, files: dict[str, C._Model]) -> C.DiffFile | None:
    snap, source = load_snapshot(cfg, prev)
    if snap is None:
        print(f"[export] previous release {prev}: no snapshot in state_dir and no folder in output/data — "
              "diff.json skipped")
        return None
    lineage = {t.id: {"event": t.lineage.event, "parents": t.lineage.parents} for t in files["topics.json"].topics}
    d = quarter_diff(release_snapshot(release, files), snap, lineage, int(cfg["changes"]["movers"]),
                     float(cfg["changes"]["min_share_delta"]))
    return C.DiffFile(previous_source=source, **d)


def _label_stats(cfg: dict, labels: pd.DataFrame) -> C.LabelStats:
    src = labels["label_source"] if "label_source" in labels else pd.Series("keywords", index=labels.index)
    return C.LabelStats(provider=cfg["labeling"]["provider"], llm=int((src == "llm").sum()),
                        keywords=int((src == "keywords").sum()), overrides=int((src == "override").sum()),
                        reused=int((src == "reused").sum()))


def _llm_stats(cfg: dict, work: Path, brief: dict, release: str) -> list[C.LlmTaskStats]:
    """Per LLM task: items, cache hits, new calls, repairs and fallbacks of the last run; cost_usd = the release's
    whole spend on the task (sum of its journal), this_run_cost_usd = the last run's."""
    found = []
    lab = _read_json(work / "05_labels_meta.json")
    if lab.get("provider") == "llm":
        found.append({**lab, "task": "label", "model": lab.get("model_id", ""),
                      "items": int(lab.get("topics", 0)) - int(lab.get("reused", 0))})     # reused names: no LLM item
    merge = _read_json(work / "05_merge_meta.json").get("llm")
    found += [merge] if merge else []
    found += list((brief.get("llm") or {}).values())
    methods_llm = _read_json(work / "12_methods_meta.json").get("llm")
    found += [methods_llm] if methods_llm else []
    keys = ("from_cache", "generated", "repaired", "fallback")
    return [C.LlmTaskStats(task=s["task"], model=str(s.get("model", "")), items=int(s.get("items", 0)),
                           **{k: int(s.get(k, 0)) for k in keys}, cost_usd=round(release_spend(cfg, s["task"], release), 4),
                           this_run_cost_usd=round(float(s.get("cost_usd", 0.0)), 4))
            for s in found]


def _dump(model: C._Model) -> bytes:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def write_release(cfg: dict) -> Path:
    files = build_release(cfg)
    release = work_release(cfg)
    root = Path(cfg["pipeline"]["output_dir"]) / "data"
    out = root / release
    if out.exists():
        shutil.rmtree(out)                         # a re-run of the same release replaces it completely
    entries = []
    for rel, model in sorted(files.items()):
        if rel == "manifest.json":
            continue
        data = _dump(model)
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        entries.append(C.FileEntry(path=rel, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    manifest = files["manifest.json"].model_copy(update={"files": entries})
    (out / "manifest.json").write_bytes(_dump(C.Manifest.model_validate(manifest.model_dump())))
    write_snapshot(cfg, release, release_snapshot(release, files))     # the next quarter's diff reads it
    others = [p.name for p in root.iterdir() if (p / "manifest.json").exists() and p.name != release]
    if is_newest(release, others, known_releases(cfg)):            # re-exporting an older quarter never moves latest.json back
        latest = C.Latest(release=release, path=f"{release}/manifest.json", generated_at=manifest.generated_at)
        (root / "latest.json").write_bytes(_dump(latest))
    else:
        print(f"[export] a newer release than {release} is in {root} — latest.json left unchanged")
    print(f"[export] contract v2 → {out} ({len(entries)} files + manifest)")
    return out
