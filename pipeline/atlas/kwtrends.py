"""Step `kwtrends` (after search): author-keyword trends (R7) and the TH↔EN glossary → work/21_*
(export publishes kwtrends.json and topics/<id>.json glossary).

Keywords: the author keyword lists of 02_docs (keywords_th, keywords_en — "; "-joined by ingest), TH and EN
separately (the field a keyword came from is its lang). Each list is split on ";", terms are stripped and their
inner whitespace collapsed; terms group by atlas.thai.norm_key exactly as atlas.keywords does (case, spacing,
punctuation and lost tone marks fold together; keys shorter than keywords.min_key_length are dropped), counted once
per article. The published term is the most frequent written form of its key (ties: code-point order).

Trend years = the series years (06_meta.json `years`, ≤ last_complete_year) — the trimmed recent years are left out
so a keyword's share line ends where the topic trends end (series.json); `totals` = dated 02_docs articles per year
(= series.json corpus_total), `totals_th` / `totals_en` = those with ≥ 1 Thai / English author keyword. A keyword is
kept when it is in ≥ kwtrends.min_count articles over those years; the top kwtrends.max_keywords by that total
(TH and EN together; ties: lang, key).

Glossary: per article of the analysed window (atlas.checkpoints.analysed_window — series years plus the trimmed
recent years; every dated article when the series step has not run), when its Thai and English keyword lists have
the same length ≥ 1 they are paired by position. A pair is kept when both keys pass min_key_length, the Thai side
contains a Thai letter and the English side none (a copied English keyword is not a translation); counted once per
article. Per fine topic (atlas.checkpoints.article_topics): the top kwtrends.glossary_per_topic pairs with
n ≥ kwtrends.glossary_min_pairs; whole corpus: the top kwtrends.glossary_max pairs with n ≥ glossary_min_pairs
(ties: Thai key, English key). Displayed forms = the most frequent written form of each side of the pair.

  21_kw_years           lang, key, term, rank, year, count — one row per kept keyword × trend year
  21_glossary           scope (topic | all), topic_id (−1 for scope all), rank, th_key, en_key, th, en, n
  21_kwtrends_meta.json published, skipped, years, totals, totals_th, totals_en, candidates, kept,
                        paired_articles, pairs
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.checkpoints import analysed_window, article_topics_or_empty
from atlas.io_utils import read_table, text_column, write_table
from atlas.thai import THAI_LETTER, norm_key

LANGS = ("th", "en")
KW_COLUMNS = ["lang", "key", "term", "rank", "year", "count"]
GLOSSARY_COLUMNS = ["scope", "topic_id", "rank", "th_key", "en_key", "th", "en", "n"]


def split_terms(col: pd.Series) -> pd.Series:
    """Each cell → its list of keywords: split on ";", stripped, inner whitespace collapsed, empty terms dropped."""
    return col.fillna("").astype(str).map(lambda s: [" ".join(t.split()) for t in s.split(";") if t.strip()])


def _keys(terms: pd.Series) -> pd.Series:
    uniq = {t: norm_key(t) for t in pd.unique(terms)}
    return terms.map(uniq).fillna("").astype(str)


def keyword_rows(docs: pd.DataFrame, min_key_length: int) -> pd.DataFrame:
    """One row per (article, lang, key): article_id, year, lang, key, term (docs: article_id, year, keywords_*)."""
    parts = []
    for lang in LANGS:
        d = pd.DataFrame({"article_id": docs["article_id"].astype(str).to_numpy(),
                          "year": docs["year"].to_numpy(), "term": split_terms(text_column(docs, f"keywords_{lang}")).to_numpy()})
        d = d.explode("term").dropna(subset=["term"])
        d = d.assign(term=d["term"].astype(str), lang=lang)
        d["key"] = _keys(d["term"])
        parts.append(d[d["key"].str.len() >= min_key_length])
    out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    out = out.drop_duplicates(["article_id", "lang", "key"]).reset_index(drop=True)
    return out[["article_id", "year", "lang", "key", "term"]]


def _display(rows: pd.DataFrame, by: list[str], col: str) -> pd.Series:
    """Most frequent `col` per `by` group (ties: code-point order)."""
    c = rows.groupby([*by, col]).size().rename("_c").reset_index()
    c = c.sort_values([*by, "_c", col], ascending=[True] * len(by) + [False, True], kind="stable")
    return c.drop_duplicates(by).set_index(by)[col]


def keyword_trends(rows: pd.DataFrame, years: list[int], min_count: int,
                   max_keywords: int) -> tuple[pd.DataFrame, int]:
    """(21_kw_years table, number of candidate keys before the cuts) — counts per trend year of the kept keywords."""
    r = rows[rows["year"].isin(years)]
    if r.empty or not years:
        return pd.DataFrame(columns=KW_COLUMNS), 0
    by = r.groupby(["lang", "key", "year"]).size().unstack(fill_value=0).reindex(columns=years, fill_value=0)
    total = by.sum(axis=1)
    candidates = len(total)
    keep = total[total >= min_count].rename("total").reset_index()
    keep = keep.sort_values(["total", "lang", "key"], ascending=[False, True, True], kind="stable").head(max_keywords)
    if keep.empty:
        return pd.DataFrame(columns=KW_COLUMNS), candidates
    keep["rank"] = np.arange(len(keep), dtype=np.int64)
    term = _display(r, ["lang", "key"], "term")
    idx = pd.MultiIndex.from_frame(keep[["lang", "key"]])
    counts = by.loc[idx].to_numpy(dtype=np.int64)
    out = pd.DataFrame({"lang": np.repeat(keep["lang"].to_numpy(), len(years)),
                        "key": np.repeat(keep["key"].to_numpy(), len(years)),
                        "term": np.repeat(term.loc[idx].to_numpy(), len(years)),
                        "rank": np.repeat(keep["rank"].to_numpy(), len(years)),
                        "year": np.tile(np.asarray(years, dtype=np.int64), len(keep)),
                        "count": counts.reshape(-1)})
    return out[KW_COLUMNS], candidates


def glossary_pairs(docs: pd.DataFrame, min_key_length: int) -> pd.DataFrame:
    """article_id, th_key, en_key, th, en — keyword lists of equal length paired by position, one row per article
    and pair (docs: article_id, keywords_th, keywords_en)."""
    th, en = split_terms(text_column(docs, "keywords_th")), split_terms(text_column(docs, "keywords_en"))
    n_th, n_en = th.map(len), en.map(len)
    ok = (n_th == n_en) & (n_th >= 1)
    d = pd.DataFrame({"article_id": docs.loc[ok, "article_id"].astype(str).to_numpy(), "th": th[ok].to_numpy(),
                      "en": en[ok].to_numpy()})
    cols = ["article_id", "th_key", "en_key", "th", "en"]
    if d.empty:
        return pd.DataFrame(columns=cols)
    d = d.explode(["th", "en"]).dropna(subset=["th", "en"])
    d = d.assign(th=d["th"].astype(str), en=d["en"].astype(str))
    d["th_key"], d["en_key"] = _keys(d["th"]), _keys(d["en"])
    has_thai = d["th"].map(lambda s: bool(THAI_LETTER.search(s)))
    en_thai = d["en"].map(lambda s: bool(THAI_LETTER.search(s)))
    d = d[(d["th_key"].str.len() >= min_key_length) & (d["en_key"].str.len() >= min_key_length) & has_thai & ~en_thai]
    return d.drop_duplicates(["article_id", "th_key", "en_key"])[cols].reset_index(drop=True)


def glossary(pairs: pd.DataFrame, topic_of: pd.Series, per_topic: int, min_pairs: int, max_all: int) -> pd.DataFrame:
    """21_glossary — per fine topic the top `per_topic` pairs, whole corpus the top `max_all`, each with
    n ≥ min_pairs (n = articles that pair them)."""
    if pairs.empty:
        return pd.DataFrame(columns=GLOSSARY_COLUMNS)
    pk = ["th_key", "en_key"]
    th, en = _display(pairs, pk, "th"), _display(pairs, pk, "en")
    p = pairs.assign(topic_id=pairs["article_id"].map(topic_of).fillna(-1).astype(np.int64))

    def ranked(counts: pd.DataFrame, by: list[str], top: int) -> pd.DataFrame:
        counts = counts[counts["n"] >= min_pairs].sort_values([*by, "n", *pk], ascending=[True] * len(by) + [
            False, True, True], kind="stable")
        counts = counts.groupby(by).head(top) if by else counts.head(top)
        return counts.assign(rank=counts.groupby(by).cumcount() if by else np.arange(len(counts)))

    per = ranked(p[p["topic_id"] >= 0].groupby(["topic_id", *pk]).size().rename("n").reset_index(), ["topic_id"],
                 per_topic).assign(scope="topic")
    whole = ranked(p.groupby(pk).size().rename("n").reset_index(), [], max_all).assign(scope="all", topic_id=-1)
    out = pd.concat([per, whole], ignore_index=True)
    if out.empty:
        return pd.DataFrame(columns=GLOSSARY_COLUMNS)
    idx = pd.MultiIndex.from_frame(out[pk])
    out = out.assign(th=th.loc[idx].to_numpy(), en=en.loc[idx].to_numpy())
    return out.astype({"topic_id": np.int64, "rank": np.int64, "n": np.int64})[GLOSSARY_COLUMNS].reset_index(drop=True)


def _years(work: Path, dated: pd.Series) -> list[int]:
    p = work / "06_meta.json"
    if p.exists():
        return [int(y) for y in json.loads(p.read_text(encoding="utf-8")).get("years", [])]
    return sorted({int(y) for y in dated})


def kwtrends(cfg: dict) -> dict:
    work = Path(cfg["pipeline"]["work_dir"])
    kcfg = cfg["kwtrends"]
    for stale in work.glob("21_*"):          # a re-run that stops half-way must not leave the old release's tables
        stale.unlink()
    meta_path = work / "21_kwtrends_meta.json"
    if not kcfg["enabled"]:
        meta = {"published": False, "skipped": "kwtrends.enabled is false"}
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        print("[kwtrends] kwtrends.enabled is false — no keyword trends and no glossary")
        return meta
    min_len = int(cfg["keywords"]["min_key_length"])
    docs = read_table(work / "02_docs.parquet")
    docs = docs.assign(article_id=docs["article_id"].astype(str), year=pd.to_numeric(docs["year"], errors="coerce"))
    docs = docs[docs["year"].notna()].drop_duplicates("article_id")
    docs = docs.assign(year=docs["year"].astype(np.int64))
    years = _years(work, docs["year"])

    rows = keyword_rows(docs, min_len)
    trends, candidates = keyword_trends(rows, years, int(kcfg["min_count"]), int(kcfg["max_keywords"]))
    in_years = docs[docs["year"].isin(years)]
    totals = in_years.groupby("year").size().reindex(years, fill_value=0)
    per_lang = {lang: rows[(rows["lang"] == lang) & rows["year"].isin(years)].groupby("year")["article_id"]
                .nunique().reindex(years, fill_value=0) for lang in LANGS}

    win = analysed_window(work)
    gdocs = docs[docs["year"].between(*win)] if win else docs
    pairs = glossary_pairs(gdocs, min_len)
    gloss = glossary(pairs, article_topics_or_empty(work), int(kcfg["glossary_per_topic"]), int(kcfg["glossary_min_pairs"]),
                     int(kcfg["glossary_max"]))
    write_table(trends, work / "21_kw_years.parquet")
    write_table(gloss, work / "21_glossary.parquet")
    kept = int(trends["rank"].nunique()) if len(trends) else 0
    meta = {"published": True, "skipped": None, "years": years, "totals": [int(v) for v in totals],
            "totals_th": [int(v) for v in per_lang["th"]], "totals_en": [int(v) for v in per_lang["en"]],
            "candidates": int(candidates), "kept": kept, "paired_articles": int(pairs["article_id"].nunique()),
            "pairs": int(len(pairs[["th_key", "en_key"]].drop_duplicates()))}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    n_topic = int((gloss["scope"] == "topic").sum()) if len(gloss) else 0
    n_all = int((gloss["scope"] == "all").sum()) if len(gloss) else 0
    print(f"[kwtrends] {kept:,} of {candidates:,} keywords over {len(years)} years (≥ {kcfg['min_count']} articles); "
          f"glossary: {meta['pairs']:,} TH↔EN pairs from {meta['paired_articles']:,} articles → {n_all:,} listed, "
          f"{n_topic:,} topic entries")
    return meta
