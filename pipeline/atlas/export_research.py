"""Contract 2.3 files of the researchers' release (P4), built from work/19_* (references), 20_* (search, galaxy) and
21_* (keyword trends). Called by atlas.export_v2.build_release; each module is optional — a missing checkpoint leaves
its files out; a module skipped for a reason returns that reason (→ manifest.skipped_modules).

references.json    D7 reference practice per journal + R12 citations inside the corpus (when coverage allows)
search/meta.json, search/vocab.json, search/idx-<NNN>.json, search/docs-<NNN>.json
                   R2 sharded article search (atlas.search_index) — every index shard is written, even an empty one
galaxy.json        R8 article points, aligned with the search doc ordinals
kwtrends.json      R7 author-keyword trends over the series years + corpus TH↔EN glossary (atlas.kwtrends);
                   the per-topic glossary goes into topics/<id>.json
Article metadata published here: id, titles, year, journal name, topic, DOI, ThaiJO URL, "cited in TCI" count —
never an author name or an abstract.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from atlas.checkpoints import article_topics
from atlas.io_utils import json_float, read_json, read_optional, read_table
from atlas.schema import contract as C
from atlas.search_index import FIELDS, QUANT, STOPWORDS, fnv1a32


def _str(v) -> str:
    return v if isinstance(v, str) else ""


# ---------------------------------------------------------------------- references (D7, R12)
def _internal_published(meta: dict) -> bool:
    return bool(meta.get("published")) and bool(meta.get("internal"))


def cited_counts(work: Path) -> dict[str, int]:
    """{article_id: distinct corpus articles citing it} — empty unless internal citation is published."""
    meta = read_json(work / "19_refs_meta.json")
    cites = read_optional(work / "19_article_cites.parquet")
    if not _internal_published(meta) or cites is None:
        return {}
    return dict(zip(cites["article_id"].astype(str), cites["cited_in_tci"].astype(int)))


def topic_citations(work: Path) -> dict[int, tuple[int, int]] | None:
    """{topic id: (received, given)} — None unless internal citation is published."""
    meta = read_json(work / "19_refs_meta.json")
    matches = read_optional(work / "19_ref_matches.parquet")
    if not _internal_published(meta) or matches is None:
        return None
    topic_of = article_topics(work)
    got = matches["cited_id"].astype(str).map(topic_of).fillna(-1).astype(int).value_counts()
    gave = matches["citing_id"].astype(str).map(topic_of).fillna(-1).astype(int).value_counts()
    return {int(t): (int(got.get(t, 0)), int(gave.get(t, 0))) for t in set(got.index) | set(gave.index) if t >= 0}


def references_file(cfg: dict, work: Path, code: dict[int, str], jid: dict[str, str] | None = None,
                    jname: dict[str, str] | None = None) -> tuple[C.ReferencesFile | None, str | None]:
    """(references.json, None), or (None, reason) when the step skipped the module, or (None, None) when the step
    did not run."""
    meta = read_json(work / "19_refs_meta.json")
    if not meta:
        return None, None
    if not meta.get("published"):
        return None, str(meta.get("skipped") or "references module not published")
    rcfg = cfg["references"]
    jid, jname = jid or {}, jname or {}
    practice = read_optional(work / "19_journal_refs.parquet")
    journals = [C.JournalRefs(
        journal=jname.get(r.journal_key) or _str(r.journal), id=jid.get(r.journal_key), articles=int(r.articles),
        articles_with_refs=int(r.articles_with_refs), refs_median=json_float(r.refs_median, 2) or 0.0,
        age_median=json_float(r.age_median, 2), share_recent=json_float(r.share_recent), share_thai=json_float(r.share_thai) or 0.0,
        share_doi=json_float(r.share_doi) or 0.0) for r in (practice.itertuples() if practice is not None else [])]
    internal = None
    if meta.get("internal"):
        internal = _internal(cfg, work, code, meta)
    return C.ReferencesFile(
        window=C.YearWindow(start=int(meta["window"][0]), end=int(meta["window"][1])), articles=int(meta["articles"]),
        articles_with_refs=int(meta["with_refs"]), coverage=json_float(meta["coverage"]) or 0.0,
        refs_counted=int(meta["refs_counted"]), min_coverage=float(rcfg["min_coverage"]),
        min_journal_articles=int(rcfg["min_journal_articles"]), recent_years=int(rcfg["recent_years"]),
        journals=journals, internal=internal,
        internal_reason=None if internal is not None else str(meta.get("internal_reason") or "")), None


def _internal(cfg: dict, work: Path, code: dict[int, str], meta: dict) -> C.InternalCitations:
    rcfg = cfg["references"]
    n = int(meta["matches"])
    per_topic = topic_citations(work) or {}
    flows = read_optional(work / "19_topic_flows.parquet")
    flows = flows[(flows["source"] != flows["target"]) & (flows["n"] >= int(rcfg["min_flow"]))] if flows is not None \
        else pd.DataFrame(columns=["source", "target", "n"])
    cites = read_table(work / "19_article_cites.parquet").head(int(rcfg["top_articles"]))
    arts = read_table(work / "01_articles.parquet")
    arts = arts.assign(article_id=arts["article_id"].astype(str)).set_index("article_id")
    topic_of = article_topics(work)
    top = []
    for r in cites.itertuples():
        aid = str(r.article_id)
        if aid not in arts.index:
            continue
        a = arts.loc[aid]
        year = pd.to_numeric(a.get("year"), errors="coerce")
        t = int(topic_of.get(aid, -1))
        top.append(C.CitedArticle(article_id=aid, title=_str(a.get("title")) or _str(a.get("title_th")),
                                  title_en=_str(a.get("title_en")), year=int(year) if pd.notna(year) else None,
                                  journal=_str(a.get("journal_name")), url=_str(a.get("url")), doi=_str(a.get("doi")),
                                  topic=code.get(t), count=int(r.cited_in_tci)))
    methods = meta.get("methods") or {}
    return C.InternalCitations(
        matches=n, citing_articles=int(meta["citing_articles"]), cited_articles=int(meta["cited_articles"]),
        share_doi=json_float(methods.get("doi", 0) / n) if n else 0.0, share_title=json_float(methods.get("title", 0) / n) if n else 0.0,
        min_flow=int(rcfg["min_flow"]),
        topics=[C.TopicCitations(topic=code[t], received=rg[0], given=rg[1])
                for t, rg in sorted(per_topic.items()) if t in code],
        flows=[C.CitationFlow(source=code[int(f.source)], target=code[int(f.target)], n=int(f.n))
               for f in flows.itertuples() if int(f.source) in code and int(f.target) in code],
        top_articles=top)


# ---------------------------------------------------------------------- search (R2) + galaxy (R8)
def _or_none(values: pd.Series) -> list[str | None]:
    return [v if v else None for v in values.fillna("").astype(str)]


def search_files(cfg: dict, work: Path, code: dict[int, str]) -> tuple[dict[str, C._Model], dict[str, str]]:
    """({published path: model}, {module: skip reason}) for the search and galaxy modules — both empty when the
    search step did not run."""
    meta = read_json(work / "20_search_meta.json")
    if not meta:
        return {}, {}
    files: dict[str, C._Model] = {}
    skipped: dict[str, str] = {}
    smeta, gmeta = meta.get("search") or {}, meta.get("galaxy") or {}
    if not smeta.get("published"):
        skipped["search"] = str(smeta.get("skipped") or "search module not published")
        skipped["galaxy"] = str(gmeta.get("skipped") or "galaxy needs the search module")
        return files, skipped
    scfg = cfg["search"]
    n_shards, per = int(scfg["index_shards"]), int(scfg["docs_per_shard"])
    docs = read_table(work / "20_docs.parquet")
    postings = read_table(work / "20_postings.parquet")
    n = len(docs)

    # ---- vocab + index shards: postings are sorted by (token, ordinal) and unique
    tok = postings["token"].astype(str).to_numpy()
    ords = postings["ordinal"].to_numpy(dtype=np.int64)
    first = np.ones(len(tok), dtype=bool)
    first[1:] = tok[1:] != tok[:-1]
    delta = ords.copy()
    delta[1:] = np.where(first[1:], ords[1:], ords[1:] - ords[:-1])
    starts = np.flatnonzero(first)
    vocab = tok[starts].tolist()
    df = np.diff(np.append(starts, len(tok))).tolist()
    shard_of = [fnv1a32(t) % n_shards for t in vocab]
    shards: list[dict[str, list[int]]] = [{} for _ in range(n_shards)]
    for t, s, chunk in zip(vocab, shard_of, np.split(delta, starts[1:]) if len(starts) else []):
        shards[s][t] = chunk.tolist()
    files["search/vocab.json"] = C.SearchVocab(tokens=vocab, df=df)
    for s, postings_s in enumerate(shards):
        files[f"search/idx-{s:03d}.json"] = C.SearchIndexShard(shard=s, postings=postings_s)

    # ---- doc shards: [article_id, title_th, title_en, year, journal_index, topic|null, doi|null, url|null, cited]
    cited = cited_counts(work)
    ids = docs["article_id"].astype(str)
    rows = list(zip(ids, docs["title_th"].fillna("").astype(str), docs["title_en"].fillna("").astype(str),
                    docs["year"].astype(int).tolist(), docs["journal_index"].astype(int).tolist(),
                    [code.get(int(t)) for t in docs["topic_id"]], _or_none(docs["doi"]), _or_none(docs["url"]),
                    [int(cited.get(a, 0)) for a in ids]))
    n_doc_shards = -(-n // per)
    for s in range(n_doc_shards):
        files[f"search/docs-{s:03d}.json"] = C.SearchDocShard(shard=s, start=s * per, docs=rows[s * per:(s + 1) * per])
    files["search/meta.json"] = C.SearchMeta(
        tokenizer_version=int(smeta["tokenizer_version"]), n_docs=n, n_tokens=len(vocab), n_postings=len(tok),
        index_shards=n_shards, docs_per_shard=per, doc_shards=n_doc_shards, max_token_chars=int(scfg["max_token_chars"]),
        max_results=int(scfg["max_results"]), min_df=int(scfg["min_df"]), fields=list(FIELDS),
        stopwords=sorted(STOPWORDS), journals=[str(j) for j in meta.get("journals", [])],
        years=[int(y) for y in meta.get("years", [])])

    # ---- galaxy.json
    if not gmeta.get("published"):
        skipped["galaxy"] = str(gmeta.get("skipped") or "galaxy points not built")
        return files, skipped
    pts = read_table(work / "20_galaxy_points.parquet").sort_values("ordinal")
    topics = sorted(code.values())
    tindex = {t: i for i, t in enumerate(topics)}
    x0, y0, x1, y1 = (float(v) for v in gmeta["bounds"])
    files["galaxy.json"] = C.GalaxyFile(
        n=len(pts), scale=QUANT, bounds=C.GalaxyBounds(x0=x0, y0=y0, x1=x1, y1=y1), topics=topics,
        x=pts["x"].astype(int).tolist(), y=pts["y"].astype(int).tolist(),
        t=[tindex.get(code.get(int(t), ""), -1) for t in pts["topic_id"]], yr=pts["year"].astype(int).tolist())
    return files, skipped


# ---------------------------------------------------------------------- keyword trends + glossary (R7)
def kwtrends_file(cfg: dict, work: Path, code: dict[int, str]) -> tuple[
        C.KwTrendsFile | None, str | None, dict[int, list[C.GlossaryItem]] | None]:
    """(kwtrends.json, None, {topic id: glossary}) — or (None, reason, None) when the step skipped the module, or
    (None, None, None) when the step did not run. Topics without pairs are absent from the dict (→ [])."""
    meta = read_json(work / "21_kwtrends_meta.json")
    if not meta:
        return None, None, None
    if not meta.get("published"):
        return None, str(meta.get("skipped") or "kwtrends module not published"), None
    kcfg = cfg["kwtrends"]
    years = [int(y) for y in meta["years"]]
    kw = read_table(work / "21_kw_years.parquet")
    keywords = []
    for _, g in kw.sort_values(["rank", "year"], kind="stable").groupby("rank", sort=True):
        counts = g.set_index("year")["count"].reindex(years, fill_value=0).astype(int).tolist()
        keywords.append(C.KeywordTrend(term=str(g["term"].iloc[0]), lang=str(g["lang"].iloc[0]), n=sum(counts),
                                       counts=counts))
    gl = read_table(work / "21_glossary.parquet").sort_values(["scope", "topic_id", "rank"], kind="stable")

    def items(rows: pd.DataFrame) -> list[C.GlossaryItem]:
        return [C.GlossaryItem(th=str(r.th), en=str(r.en), n=int(r.n)) for r in rows.itertuples()]

    per_topic = {int(t): items(g) for t, g in gl[gl["scope"] == "topic"].groupby("topic_id") if int(t) in code}
    model = C.KwTrendsFile(
        years=years, totals=[int(v) for v in meta["totals"]], totals_th=[int(v) for v in meta["totals_th"]],
        totals_en=[int(v) for v in meta["totals_en"]], min_count=int(kcfg["min_count"]),
        max_keywords=int(kcfg["max_keywords"]), glossary_min_pairs=int(kcfg["glossary_min_pairs"]),
        keywords=keywords, glossary=items(gl[gl["scope"] == "all"]))
    return model, None, per_topic
