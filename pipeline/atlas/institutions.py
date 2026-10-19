"""Step `institutions` (after match): institutions, collaboration and provinces → work/15_* (export publishes them).

Every author row is resolved to a canonical institution (atlas.institutions_ref); an article counts once for each
institution among its authors (full counting). W = the last institutions.window_years complete years (06_meta.json
last_complete_year), R = the emerging recent window.

  15_article_institutions   article_id, inst_key — distinct pairs, all years (internal: gaps and export read it)
  15_institutions           one row per institution: inst_key, code, name_th, name_en, type, province, country,
                            source, ror, articles (W), articles_total, articles_recent (R), intl_share (W: share of its
                            articles that pair Thai and foreign institutions), partners (published co-authors in W),
                            topics (W), published (≥ institutions.min_articles in W)
  15_inst_years             inst_key, year, articles (published institutions)
  15_inst_topics            inst_key, topic_id, count, share (W, published institutions)
  15_inst_pairs             a, b, articles — co-authored articles in W between published institutions,
                            ≥ network_min_articles, the network_max_edges largest
  15_inst_countries         inst_key ("" = the whole corpus), country, articles — articles in W pairing a Thai (or
                            unplaced) institution with one in that foreign country (published institutions only)
  15_inst_suggest           inst_key, other_key, similarity, topics ("1;7;9") — R6: published institutions with the
                            most similar topic mix (cosine ≥ suggest_min_similarity) and no co-authored article in W
  15_provinces              code, articles, articles_recent, institutions — articles with ≥ 1 author placed in the
                            province (once per province), published institutions placed there
  15_regions                region, articles
  15_institutions_meta.json windows, coverage, KPI shares, sources, population
Author rows are read for their affiliations only — the name columns are dropped on read (PDPA).
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.institutions_ref import Institution, Resolver, inst_code, load_aliases, load_ror
from atlas.io_utils import read_table, write_table
from atlas.orgs import org_display_names
from atlas.places import provinces, region_of
from atlas.thai import thai_ratio

INST_COLUMNS = ["inst_key", "code", "name_th", "name_en", "type", "province", "country", "source", "ror",
                "articles", "articles_total", "articles_recent", "intl_share", "partners", "topics", "published"]
AUTHOR_COLUMNS = ["article_id", "affiliation_th", "affiliation_en", "org_key"]
IDENT_COLUMNS = ["name_th", "name_en", "type", "province", "country", "source", "ror"]


def windows(cfg: dict, last: int) -> dict[str, tuple[int, int]]:
    r0 = last - int(cfg["emerging"]["recent_window"]) + 1
    return {"W": (last - int(cfg["institutions"]["window_years"]) + 1, last), "R": (r0, last)}


def _in(years: pd.Series, span: tuple[int, int]) -> pd.Series:
    return years.between(*span).fillna(False).astype(bool)


def _text(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].fillna("").astype(str) if col in df.columns else pd.Series("", index=df.index, dtype=str)


def _given(v) -> bool:
    return isinstance(v, str) and v != ""


def _mode(s: pd.Series):
    """Most frequent non-empty value (ties: alphabetically first); None when there is none."""
    s = s[s.map(_given)]
    if s.empty:
        return None
    vc = s.value_counts()
    return sorted(vc[vc == vc.max()].index)[0]


def resolve_authors(authors: pd.DataFrame, resolver: Resolver, display: dict[str, str]
                    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(article_id, inst_key) distinct, and one identity row per inst_key. Each distinct affiliation is resolved once;
    an institution's province and country are the most frequent among its author rows; an institution known only as
    written takes the P1 display name of its org_key (most frequent written form)."""
    a = pd.DataFrame({"article_id": authors["article_id"], "th": _text(authors, "affiliation_th"),
                      "en": _text(authors, "affiliation_en"), "org_key": _text(authors, "org_key")})
    trip = a[["th", "en", "org_key"]].drop_duplicates().reset_index(drop=True)
    found: list[Institution | None] = [resolver.resolve(t, e, k) for t, e, k in zip(trip["th"], trip["en"], trip["org_key"])]
    res = pd.DataFrame([asdict(f) if f is not None else {"key": ""} for f in found],
                       columns=["key", *IDENT_COLUMNS]).rename(columns={"key": "inst_key"})
    rows = a.merge(pd.concat([trip, res], axis=1), on=["th", "en", "org_key"], how="left")
    rows = rows[rows["inst_key"].map(_given)]
    links = rows[["article_id", "inst_key"]].drop_duplicates().reset_index(drop=True)
    ident = rows.groupby("inst_key").agg(
        name_th=("name_th", "first"), name_en=("name_en", "first"), type=("type", "first"),
        province=("province", _mode), country=("country", _mode), source=("source", "first"), ror=("ror", "first"),
        org_key=("org_key", "first")).reset_index()
    th_out, en_out = [], []
    for k, th, en, src in zip(ident["org_key"], ident["name_th"].fillna(""), ident["name_en"].fillna(""),
                              ident["source"]):
        if src == "name":
            shown = display.get(k) or th or en
            th, en = (shown, "") if thai_ratio(shown) > 0.5 else ("", shown)
        th_out.append(str(th))
        en_out.append(str(en))
    ident["name_th"], ident["name_en"] = th_out, en_out
    ident["country"] = [c if _given(c) else ("TH" if _given(p) else None)
                        for c, p in zip(ident["country"], ident["province"])]
    ident["province"] = [p if _given(p) else None for p in ident["province"]]
    ident["ror"] = ident["ror"].fillna("").astype(str)
    return links, ident.drop(columns=["org_key"])


def suggest(mix: pd.DataFrame, coauthored: set[tuple[str, str]], k: int, min_sim: float, chunk: int = 512
            ) -> pd.DataFrame:
    """R6 — for each institution of `mix` (inst_key, topic_id, share) the k most similar others (cosine of topic
    shares ≥ min_sim) that it has not co-authored with; topics = up to 3 topics both work on (largest common share)."""
    cols = ["inst_key", "other_key", "similarity", "topics"]
    if mix.empty or k == 0:
        return pd.DataFrame(columns=cols)
    insts = sorted(mix["inst_key"].unique())
    topics = sorted(mix["topic_id"].unique())
    ii, ti = {x: i for i, x in enumerate(insts)}, {t: i for i, t in enumerate(topics)}
    m = np.zeros((len(insts), len(topics)))
    m[mix["inst_key"].map(ii).to_numpy(), mix["topic_id"].map(ti).to_numpy()] = mix["share"].to_numpy(dtype=float)
    unit = m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-12)
    rows = []
    for s in range(0, len(insts), chunk):
        sim = unit[s:s + chunk] @ unit.T
        for r, i in enumerate(range(s, min(s + chunk, len(insts)))):
            sim[r, i] = -1.0
            picked = 0
            for j in np.argsort(-sim[r], kind="stable"):
                if picked >= k or sim[r, j] < min_sim:
                    break
                a, b = insts[i], insts[j]
                if (min(a, b), max(a, b)) in coauthored:
                    continue
                common = np.minimum(m[i], m[j])
                shared = [topics[t] for t in np.argsort(-common, kind="stable")[:3] if common[t] > 0]
                rows.append({"inst_key": a, "other_key": b, "similarity": round(float(sim[r, j]), 4),
                             "topics": ";".join(str(int(t)) for t in shared)})
                picked += 1
    return pd.DataFrame(rows, columns=cols)


def load_population(path: str | Path | None) -> dict | None:
    """{"year": int | None, "by_code": {province code: population}} from registry/province_population.csv, or None."""
    if not path or not Path(path).exists():
        return None
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    known, by, years = provinces(), {}, set()
    for n, r in enumerate(df.to_dict("records"), start=2):
        code = str(r.get("code", "")).strip().upper()
        if code not in known:
            raise ValueError(f"{path} row {n}: {code!r} is not a province code of atlas/data/th_provinces.csv")
        pop = int(str(r.get("population", "")).replace(",", "").strip() or 0)
        if pop <= 0:
            raise ValueError(f"{path} row {n}: population must be a positive whole number")
        by[code] = pop
        if str(r.get("year", "")).strip():
            years.add(int(r["year"]))
    return {"year": max(years) if years else None, "by_code": by} if by else None


def institutions(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    icfg = cfg["institutions"]
    for stale in work.glob("15_*"):          # a re-run that stops half-way must not leave the old release's tables
        stale.unlink()
    if not icfg["enabled"]:
        print("[institutions] institutions.enabled is false — no institutions module")
        return pd.DataFrame(columns=INST_COLUMNS)
    last = int(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["last_complete_year"])
    win = windows(cfg, last)
    W, R = win["W"], win["R"]
    arts = read_table(work / "01_articles.parquet")[["article_id", "year"]]
    arts = arts.assign(year=pd.to_numeric(arts["year"], errors="coerce"))
    try:
        authors = read_table(work / "01_authors.parquet")
    except FileNotFoundError:
        authors = pd.DataFrame(columns=AUTHOR_COLUMNS)
    authors = authors[[c for c in AUTHOR_COLUMNS if c in authors.columns]]      # affiliations only — never a name
    ror = load_ror(icfg["ror_path"], cfg["taxonomy"]["openalex"]["country_code"],
                   Path(cfg["pipeline"]["state_dir"]) / "ror")
    resolver = Resolver(load_aliases(icfg["aliases_path"], int(icfg["alias_min_chars"])), ror,
                        bool(icfg["province_from_name"]))
    links, ident = resolve_authors(authors, resolver, org_display_names(authors))
    links = links.merge(arts, on="article_id", how="inner")

    # ---- counts, publication rule, international collaboration
    country = ident.set_index("inst_key")["country"]
    lw = links[_in(links["year"], W)].copy()
    lw["foreign"] = lw["inst_key"].map(country).map(lambda c: _given(c) and c != "TH").astype(bool)
    per_w = lw.groupby("inst_key")["article_id"].nunique()
    per_r = links[_in(links["year"], R)].groupby("inst_key")["article_id"].nunique()
    per_all = links.groupby("inst_key")["article_id"].nunique()
    published = set(per_w[per_w >= int(icfg["min_articles"])].index)
    intl = set(lw.loc[lw["foreign"], "article_id"]) & set(lw.loc[~lw["foreign"], "article_id"])
    lw["intl"] = lw["article_id"].isin(intl).astype(bool)
    with_org = int(lw["article_id"].nunique())
    multi = int((lw.groupby("article_id")["inst_key"].nunique() >= 2).sum())

    # ---- network among published institutions
    pw = lw.loc[lw["inst_key"].isin(published), ["article_id", "inst_key"]]
    both = pw.merge(pw, on="article_id")
    both = both[both["inst_key_x"] < both["inst_key_y"]]
    pairs = (both.groupby(["inst_key_x", "inst_key_y"]).size().rename("articles").reset_index()
             .rename(columns={"inst_key_x": "a", "inst_key_y": "b"}))
    partners = pd.concat([pairs["a"], pairs["b"]]).value_counts()
    edges = (pairs[pairs["articles"] >= int(icfg["network_min_articles"])]
             .sort_values(["articles", "a", "b"], ascending=[False, True, True]).head(int(icfg["network_max_edges"])))

    # ---- topics (W) and R6 suggestions
    docs = read_table(work / "02_docs.parquet")[["article_id"]]
    fine = read_table(work / "04_fine_topics.parquet")[["article_id", "fine_topic"]]
    topic_of = docs.merge(fine, on="article_id").rename(columns={"fine_topic": "topic_id"})
    topic_of = topic_of[topic_of["topic_id"].fillna(-1).astype(int) >= 0].astype({"topic_id": int})
    lwt = lw[["article_id", "inst_key"]].merge(topic_of, on="article_id")
    n_topics = lwt.groupby("inst_key")["topic_id"].nunique()
    mix = lwt[lwt["inst_key"].isin(published)].groupby(["inst_key", "topic_id"]).size().rename("count").reset_index()
    mix["share"] = mix["count"] / mix.groupby("inst_key")["count"].transform("sum")
    mix = mix.sort_values(["inst_key", "count", "topic_id"], ascending=[True, False, True]).reset_index(drop=True)
    coauthored = set(zip(pairs["a"], pairs["b"]))
    sugg = suggest(mix, coauthored, int(icfg["suggest_k"]), float(icfg["suggest_min_similarity"]))

    # ---- years and partner countries
    dated = links[links["inst_key"].isin(published) & links["year"].notna() & (links["year"] <= last)]
    years = dated.astype({"year": int}).groupby(["inst_key", "year"]).size().rename("articles").reset_index()
    foreign_side = lw.loc[lw["intl"] & lw["foreign"], ["article_id", "inst_key"]]
    foreign_side = foreign_side.assign(country=foreign_side["inst_key"].map(country))[["article_id", "country"]]
    foreign_side = foreign_side.drop_duplicates()
    national = foreign_side.groupby("country").size().rename("articles").reset_index().assign(inst_key="")
    home = lw.loc[lw["intl"] & ~lw["foreign"] & lw["inst_key"].isin(published), ["article_id", "inst_key"]]
    per_inst = (home.merge(foreign_side, on="article_id").drop_duplicates(["inst_key", "article_id", "country"])
                .groupby(["inst_key", "country"]).size().rename("articles").reset_index()
                .sort_values(["inst_key", "articles", "country"], ascending=[True, False, True])
                .groupby("inst_key").head(int(icfg["max_partners"])))
    countries = pd.concat([national, per_inst], ignore_index=True)[["inst_key", "country", "articles"]]

    # ---- provinces and regions (articles once per province of their authors)
    placed = links.assign(province=links["inst_key"].map(ident.set_index("inst_key")["province"]))
    placed = placed[placed["province"].map(_given)]
    pwy = placed[_in(placed["year"], W)][["article_id", "province"]].drop_duplicates()
    pry = placed[_in(placed["year"], R)][["article_id", "province"]].drop_duplicates()
    pub = ident[ident["inst_key"].isin(published) & ident["province"].map(_given)]
    prov = pd.DataFrame({"articles": pwy.groupby("province").size(), "articles_recent": pry.groupby("province").size(),
                         "institutions": pub.groupby("province").size()}).fillna(0).astype(int)
    prov = prov.rename_axis("code").reset_index().sort_values("code")
    regions = (pwy.assign(region=pwy["province"].map(region_of))[["article_id", "region"]].drop_duplicates()
               .groupby("region").size().rename("articles").reset_index())

    # ---- the institutions table
    intl_share = lw.groupby("inst_key")["intl"].mean()
    out = ident.assign(
        code=ident["inst_key"].map(inst_code), articles=ident["inst_key"].map(per_w).fillna(0).astype(int),
        articles_total=ident["inst_key"].map(per_all).fillna(0).astype(int),
        articles_recent=ident["inst_key"].map(per_r).fillna(0).astype(int),
        intl_share=ident["inst_key"].map(intl_share).astype(float),
        partners=ident["inst_key"].map(partners).fillna(0).astype(int),
        topics=ident["inst_key"].map(n_topics).fillna(0).astype(int),
        published=ident["inst_key"].isin(published))[INST_COLUMNS]

    write_table(links[["article_id", "inst_key"]], work / "15_article_institutions.parquet")
    write_table(out, work / "15_institutions.parquet")
    write_table(years, work / "15_inst_years.parquet")
    write_table(mix, work / "15_inst_topics.parquet")
    write_table(edges.reset_index(drop=True), work / "15_inst_pairs.parquet")
    write_table(countries, work / "15_inst_countries.parquet")
    write_table(sugg, work / "15_inst_suggest.parquet")
    write_table(prov, work / "15_provinces.parquet")
    write_table(regions, work / "15_regions.parquet")
    meta = {
        "windows": {k: list(v) for k, v in win.items()}, "articles_window": int(_in(arts["year"], W).sum()),
        "with_org": with_org, "located": int(pwy["article_id"].nunique()),
        "pct_international": round(len(intl) / with_org, 6) if with_org else None,
        "pct_multi_institution": round(multi / with_org, 6) if with_org else None,
        "institutions_total": int(len(ident)), "published": len(published),
        "sources": {str(k): int(v) for k, v in out.loc[out["published"], "source"].value_counts().items()},
        "aliases": len(resolver.alias_to_id), "ror_records": len(ror),
        "population": load_population(icfg["population_path"]),
    }
    (work / "15_institutions_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[institutions] {len(ident):,} institutions ({len(published):,} with ≥ {icfg['min_articles']} articles in "
          f"{W[0]}–{W[1]}); {len(edges):,} partnerships; {meta['located']:,} of {with_org:,} articles placed in a province")
    return out
