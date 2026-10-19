"""Step `references` (after gaps): reference practice per journal (D7) and citations inside the TCI corpus (R12)
→ work/19_* (export publishes references.json, cited_in_tci per article and per topic).

Counted references = not a self-citation and not a translated duplicate (flags from ingest). The window is the
analysed corpus (atlas.checkpoints.analysed_window); coverage = share of window articles with ≥ 1 counted reference.
The module is published only when coverage ≥ references.min_coverage; internal citation only when it found
≥ references.min_internal_matches matches — otherwise the meta names the reason (with the number).

Internal citation: a counted reference cites a corpus article when (a) its DOI (10.NNNN/…, lower case, trailing
punctuation stripped) is the DOI of exactly one article, else (b) one of its segments (split on ". ", ".", "? ") is,
once normalised (case folded, Thai tone marks, spaces and punctuation dropped), the Thai or English title of exactly
one article (titles of ≥ references.min_title_chars normalised characters; a title shared by two articles never
matches). Self-matches are dropped; an article cited several times by one article counts once.

  19_ref_matches     citing_id, cited_id, method ("doi" | "title")
  19_article_cites   article_id, cited_in_tci — distinct citing articles (> 0 only)
  19_journal_refs    journal_key, journal, articles, articles_with_refs, refs_median, age_median, share_recent,
                     share_thai, share_doi — journals with ≥ references.min_journal_articles window articles with refs
  19_topic_flows     source, target, n — citing topic → cited topic (assigned topics; same-topic pairs included)
  19_refs_meta.json  window, coverage, counts, matching methods, published / skipped, internal / internal_reason
Only article ids and counts leave this step: no reference text, no author name, no abstract.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from atlas.checkpoints import analysed_window, article_topics
from atlas.io_utils import read_table, write_table
from atlas.registry import journal_keys
from atlas.thai import THAI_MARKS

DOI = r"10\.\d{4,9}/\S+"
_TRAILING = ".,;:)]}>\"'" + "\N{RIGHT DOUBLE QUOTATION MARK}\N{RIGHT SINGLE QUOTATION MARK}"
SEGMENT_SPLIT = r"\.\s?|\?\s"                       # ". " / "." / "? "
_KEY_DROP = "[^0-9a-z\N{THAI CHARACTER KO KAI}-\N{THAI DIGIT NINE}]+"
MATCH_COLUMNS = ["citing_id", "cited_id", "method"]
JOURNAL_COLUMNS = ["journal_key", "journal", "articles", "articles_with_refs", "refs_median", "age_median",
                   "share_recent", "share_thai", "share_doi"]


def _text(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].fillna("").astype(str) if col in df.columns else pd.Series("", index=df.index, dtype=str)


def doi_of(texts: pd.Series) -> pd.Series:
    """The first DOI in each text (lower case, trailing punctuation stripped); "" when there is none."""
    found = texts.fillna("").astype(str).str.lower().str.extract(f"({DOI})", expand=False)
    return found.fillna("").astype(str).str.rstrip(_TRAILING)


def title_keys(texts: pd.Series) -> pd.Series:
    """Normalised title key: NFC, case folded, Thai tone marks and every non-letter/digit dropped (Thai kept)."""
    s = texts.fillna("").astype(str).str.normalize("NFC").str.casefold()
    return s.str.replace(THAI_MARKS.pattern, "", regex=True).str.replace(_KEY_DROP, "", regex=True)


def counted_references(refs: pd.DataFrame) -> pd.DataFrame:
    """References that count: not a self-citation, not a translated duplicate."""
    keep = pd.Series(True, index=refs.index)
    for flag in ("self_citation", "translated"):
        if flag in refs.columns:
            keep &= ~refs[flag].fillna(False).astype(bool)
    return refs[keep]


def match_references(articles: pd.DataFrame, refs: pd.DataFrame, min_title_chars: int) -> pd.DataFrame:
    """(citing_id, cited_id, method) — one row per citing article × cited corpus article (DOI first, else title).

    `articles`: article_id, doi, title_th, title_en; `refs`: article_id, text (+ self_citation, translated)."""
    refs = counted_references(refs)
    if refs.empty or articles.empty:
        return pd.DataFrame(columns=MATCH_COLUMNS)
    ids = articles["article_id"].astype(str)
    refs = refs.assign(ref=range(len(refs)), citing_id=refs["article_id"].astype(str).to_numpy())

    # (a) DOI — only a DOI that belongs to exactly one article
    adoi = pd.DataFrame({"cited_id": ids.to_numpy(), "doi": doi_of(_text(articles, "doi")).to_numpy()})
    adoi = adoi[adoi["doi"] != ""].drop_duplicates()
    adoi = adoi[~adoi["doi"].duplicated(keep=False)]
    rdoi = pd.DataFrame({"ref": refs["ref"].to_numpy(), "doi": doi_of(refs["text"]).to_numpy()})
    by_doi = rdoi[rdoi["doi"] != ""].merge(adoi, on="doi")[["ref", "cited_id"]].assign(method="doi")

    # (b) title segment — titles that occur once only, segments of refs without a DOI match
    keys = pd.concat([pd.DataFrame({"cited_id": ids.to_numpy(), "key": title_keys(_text(articles, c)).to_numpy()})
                      for c in ("title_th", "title_en")])
    keys = keys[keys["key"].str.len() >= min_title_chars].drop_duplicates()
    keys = keys[~keys["key"].duplicated(keep=False)]
    rest = refs[~refs["ref"].isin(set(by_doi["ref"]))]
    seg = pd.DataFrame({"ref": rest["ref"].to_numpy(),
                        "segment": rest["text"].fillna("").astype(str).str.split(SEGMENT_SPLIT, regex=True).to_numpy()})
    seg = seg.explode("segment").dropna(subset=["segment"])
    seg = seg[seg["segment"].str.len() >= min_title_chars]          # a key is never longer than its text
    uniq = pd.Series(seg["segment"].unique())
    key_of = pd.Series(title_keys(uniq).to_numpy(), index=uniq.to_numpy())
    seg = seg.assign(key=seg["segment"].map(key_of))
    hits = seg[seg["key"].str.len() >= min_title_chars].merge(keys, on="key")[["ref", "cited_id"]].drop_duplicates()
    hits = hits[hits.groupby("ref")["cited_id"].transform("nunique") == 1]   # two different articles: ambiguous
    by_title = hits.assign(method="title")

    m = pd.concat([by_doi, by_title], ignore_index=True).merge(refs[["ref", "citing_id"]], on="ref")
    m = m[m["citing_id"] != m["cited_id"]]                            # an article never cites itself
    m = m.sort_values(["citing_id", "cited_id", "method"]).drop_duplicates(["citing_id", "cited_id"])
    return m[MATCH_COLUMNS].reset_index(drop=True)


def journal_practice(articles: pd.DataFrame, refs: pd.DataFrame, min_articles: int, recent_years: int
                     ) -> pd.DataFrame:
    """D7 per journal over `articles` (article_id, year, journal_key, journal) and their counted `refs`
    (article_id, text, year, lang): journals with ≥ min_articles articles that have references."""
    per = refs.groupby("article_id").size()
    a = articles.assign(n_refs=articles["article_id"].map(per).fillna(0).astype(int))
    ref_year = pd.to_numeric(refs["year"], errors="coerce") if "year" in refs.columns else pd.Series(
        float("nan"), index=refs.index)
    r = refs[["article_id"]].assign(ref_year=ref_year, lang=_text(refs, "lang"), text=_text(refs, "text"))
    r = r.merge(a[["article_id", "year", "journal_key"]], on="article_id")
    age = pd.to_numeric(r["year"], errors="coerce") - r["ref_year"]
    r = r.assign(age=age.where(age >= 0), thai=r["lang"] == "th",     # a reference "from the future" is a parse error
                 has_doi=doi_of(r["text"]) != "")
    has = a[(a["n_refs"] > 0) & (a["journal_key"] != "")]
    out = has.groupby("journal_key").agg(articles_with_refs=("article_id", "size"), refs_median=("n_refs", "median"))
    out = out[out["articles_with_refs"] >= min_articles]
    if out.empty:
        return pd.DataFrame(columns=JOURNAL_COLUMNS)
    r = r[r["journal_key"].isin(out.index)]
    aged = r.dropna(subset=["age"])
    out = out.join([
        a.groupby("journal_key").size().rename("articles"),
        a.groupby("journal_key")["journal"].agg(lambda x: x.value_counts().index[0]).rename("journal"),
        r.groupby("journal_key").agg(share_thai=("thai", "mean"), share_doi=("has_doi", "mean")),
        aged.assign(recent=aged["age"] <= recent_years).groupby("journal_key").agg(
            age_median=("age", "median"), share_recent=("recent", "mean"))])
    out = out.reset_index().astype({"articles": int, "articles_with_refs": int, "refs_median": float})
    out[["share_thai", "share_doi"]] = out[["share_thai", "share_doi"]].fillna(0.0).astype(float)
    for c in ("age_median", "share_recent"):
        out[c] = out[c].astype(float)
    return out[JOURNAL_COLUMNS].sort_values(["articles_with_refs", "journal_key"], ascending=[False, True]
                                            ).reset_index(drop=True)


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def references(cfg: dict) -> dict:
    work = Path(cfg["pipeline"]["work_dir"])
    rcfg = cfg["references"]
    for stale in work.glob("19_*"):          # a re-run that stops half-way must not leave the old release's tables
        stale.unlink()
    meta_path = work / "19_refs_meta.json"
    if not rcfg["enabled"]:
        meta = {"published": False, "skipped": "references.enabled is false"}
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        print("[references] references.enabled is false — no references module")
        return meta
    arts = read_table(work / "01_articles.parquet")
    arts = arts.assign(article_id=arts["article_id"].astype(str), year=pd.to_numeric(arts["year"], errors="coerce"))
    try:
        refs = read_table(work / "01_references.parquet")
    except FileNotFoundError:
        refs = pd.DataFrame(columns=["article_id", "position", "text", "year", "lang", "translated", "self_citation"])
    refs = counted_references(refs.assign(article_id=refs["article_id"].astype(str)))

    win = analysed_window(work)
    dated = arts["year"].notna()
    in_win = dated & (arts["year"].between(*win) if win else True)
    w = arts.loc[in_win, ["article_id", "year", "journal_name"]].rename(columns={"journal_name": "journal"})
    w = w.assign(journal_key=journal_keys(w.rename(columns={"journal": "journal_name"})).to_numpy(),
                 journal=_text(w, "journal"))
    wrefs = refs[refs["article_id"].isin(set(w["article_id"]))]
    with_refs = int(wrefs["article_id"].nunique())
    coverage = with_refs / len(w) if len(w) else 0.0
    span = [int(w["year"].min()), int(w["year"].max())] if len(w) else list(win or (0, 0))

    practice = journal_practice(w, wrefs, int(rcfg["min_journal_articles"]), int(rcfg["recent_years"]))
    matches = match_references(arts, refs, int(rcfg["min_title_chars"]))
    cites = (matches.groupby("cited_id")["citing_id"].nunique().rename("cited_in_tci").rename_axis("article_id")
             .reset_index().sort_values(["cited_in_tci", "article_id"], ascending=[False, True]))
    topic_of = article_topics(work)
    t = matches.assign(source=matches["citing_id"].map(topic_of).fillna(-1).astype(int),
                       target=matches["cited_id"].map(topic_of).fillna(-1).astype(int))
    flows = (t[(t["source"] >= 0) & (t["target"] >= 0)].groupby(["source", "target"]).size().rename("n")
             .reset_index().sort_values(["n", "source", "target"], ascending=[False, True, True]))

    published = coverage >= float(rcfg["min_coverage"])
    skipped = None if published else (
        f"reference coverage {_pct(coverage)} of {len(w):,} articles {span[0]}–{span[1]} "
        f"(< references.min_coverage {_pct(float(rcfg['min_coverage']))})")
    internal = len(matches) >= int(rcfg["min_internal_matches"])
    internal_reason = None if internal else (
        f"{len(matches):,} references matched a corpus article (< references.min_internal_matches "
        f"{int(rcfg['min_internal_matches'])})")
    write_table(matches, work / "19_ref_matches.parquet")
    write_table(cites, work / "19_article_cites.parquet")
    write_table(practice, work / "19_journal_refs.parquet")
    write_table(flows.reset_index(drop=True), work / "19_topic_flows.parquet")
    meta = {"window": span, "articles": len(w), "with_refs": with_refs, "coverage": round(coverage, 6),
            "refs_counted": int(len(wrefs)), "matches": int(len(matches)),
            "methods": {k: int((matches["method"] == k).sum()) for k in ("doi", "title")},
            "citing_articles": int(matches["citing_id"].nunique()), "cited_articles": int(len(cites)),
            "published": bool(published), "skipped": skipped, "internal": bool(internal),
            "internal_reason": internal_reason}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[references] coverage {_pct(coverage)} ({with_refs:,} of {len(w):,} articles {span[0]}–{span[1]} have "
          f"counted references); {len(practice):,} journals with ≥ {rcfg['min_journal_articles']} such articles; "
          f"{len(matches):,} citations inside the corpus ({meta['methods']['doi']:,} by DOI, "
          f"{meta['methods']['title']:,} by title)" + (f" — module skipped: {skipped}" if skipped else ""))
    return meta
