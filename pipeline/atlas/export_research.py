"""Contract 2.3 files of the researchers' release (P4), built from work/19_* (references), 20_* (search, galaxy) and
21_* (keyword trends). Called by atlas.export_v2.build_release; each module is optional — a missing checkpoint leaves
its files out; a module skipped for a reason returns that reason (→ manifest.skipped_modules).

references.json    D7 reference practice per journal + R12 citations inside the corpus (when coverage allows)
Article metadata published here: id, titles, year, journal name, topic, DOI, ThaiJO URL, "cited in TCI" count —
never an author name or an abstract.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from atlas.checkpoints import article_topics
from atlas.io_utils import read_table
from atlas.schema import contract as C


def _f(v, nd: int = 4) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if math.isfinite(x) else None


def _opt(path: Path) -> pd.DataFrame | None:
    try:
        return read_table(path)
    except FileNotFoundError:
        return None


def _meta(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _str(v) -> str:
    return v if isinstance(v, str) else ""


# ---------------------------------------------------------------------- references (D7, R12)
def _internal_published(meta: dict) -> bool:
    return bool(meta.get("published")) and bool(meta.get("internal"))


def cited_counts(work: Path) -> dict[str, int]:
    """{article_id: distinct corpus articles citing it} — empty unless internal citation is published."""
    meta = _meta(work / "19_refs_meta.json")
    cites = _opt(work / "19_article_cites.parquet")
    if not _internal_published(meta) or cites is None:
        return {}
    return dict(zip(cites["article_id"].astype(str), cites["cited_in_tci"].astype(int)))


def topic_citations(work: Path) -> dict[int, tuple[int, int]] | None:
    """{topic id: (received, given)} — None unless internal citation is published."""
    meta = _meta(work / "19_refs_meta.json")
    matches = _opt(work / "19_ref_matches.parquet")
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
    meta = _meta(work / "19_refs_meta.json")
    if not meta:
        return None, None
    if not meta.get("published"):
        return None, str(meta.get("skipped") or "references module not published")
    rcfg = cfg["references"]
    jid, jname = jid or {}, jname or {}
    practice = _opt(work / "19_journal_refs.parquet")
    journals = [C.JournalRefs(
        journal=jname.get(r.journal_key) or _str(r.journal), id=jid.get(r.journal_key), articles=int(r.articles),
        articles_with_refs=int(r.articles_with_refs), refs_median=_f(r.refs_median, 2) or 0.0,
        age_median=_f(r.age_median, 2), share_recent=_f(r.share_recent), share_thai=_f(r.share_thai) or 0.0,
        share_doi=_f(r.share_doi) or 0.0) for r in (practice.itertuples() if practice is not None else [])]
    internal = None
    if meta.get("internal"):
        internal = _internal(cfg, work, code, meta)
    return C.ReferencesFile(
        window=C.YearWindow(start=int(meta["window"][0]), end=int(meta["window"][1])), articles=int(meta["articles"]),
        articles_with_refs=int(meta["with_refs"]), coverage=_f(meta["coverage"]) or 0.0,
        refs_counted=int(meta["refs_counted"]), min_coverage=float(rcfg["min_coverage"]),
        min_journal_articles=int(rcfg["min_journal_articles"]), recent_years=int(rcfg["recent_years"]),
        journals=journals, internal=internal,
        internal_reason=None if internal is not None else str(meta.get("internal_reason") or "")), None


def _internal(cfg: dict, work: Path, code: dict[int, str], meta: dict) -> C.InternalCitations:
    rcfg = cfg["references"]
    n = int(meta["matches"])
    per_topic = topic_citations(work) or {}
    flows = _opt(work / "19_topic_flows.parquet")
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
        share_doi=_f(methods.get("doi", 0) / n) if n else 0.0, share_title=_f(methods.get("title", 0) / n) if n else 0.0,
        min_flow=int(rcfg["min_flow"]),
        topics=[C.TopicCitations(topic=code[t], received=rg[0], given=rg[1])
                for t, rg in sorted(per_topic.items()) if t in code],
        flows=[C.CitationFlow(source=code[int(f.source)], target=code[int(f.target)], n=int(f.n))
               for f in flows.itertuples() if int(f.source) in code and int(f.target) in code],
        top_articles=top)
