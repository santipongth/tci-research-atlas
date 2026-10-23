"""Step `search` (after references): whole-corpus article search (R2) and the article galaxy (R8) → work/20_*
(export publishes search/meta.json, search/vocab.json, search/idx-<NNN>.json, search/docs-<NNN>.json, galaxy.json).

Doc order (atlas.search_index.doc_order): one ordinal per published article = its position in 01_articles sorted by
article_id, keeping only articles with a year in the analysed window (atlas.checkpoints.analysed_window; every dated
article when the series step has not run) and a non-empty Thai or English title. Search docs and galaxy points
share these ordinals.

Index tokens (tokens): text is normalised (NFC, NIKHAHIT + SARA AA → SARA AM, lower case, Thai digits → 0–9) and cut
into runs — a Thai run is a maximal run of Thai letters, vowels and marks (U+0E01–U+0E2E, U+0E30–U+0E3A,
U+0E40–U+0E45, U+0E47–U+0E4E; PAIYANNOI, MAIYAMOK, BAHT and Thai punctuation separate), a word run is a maximal run
of other letters/digits (str.isalnum, outside the Thai block). Thai runs are segmented with pythainlp newmm; word
runs are tokens as they are. A token is kept when it has ≥ 2 code points, is not in STOPWORDS and, if it is all
digits, has exactly 4 of them (years). The step also drops tokens longer than search.max_token_chars and tokens in
fewer than search.min_df articles. Indexed fields: title_th, title_en, keywords_th, keywords_en.

Query tokens (query_tokens) — the browser twin is web/src/lib/searchTokens.ts, pinned by
tests/fixtures/search_parity.json: the same normalisation and runs; a word run is filtered like an index token and
is `known` when it is in the vocabulary, else `unknown`; a Thai run is matched greedily — at each position the longest
substring (2 … max_token_chars code points) that is a vocabulary token or a stopword; a vocabulary token is `known`, a
stopword is consumed silently; a position where nothing matches is collected into a pending fragment, and each
maximal fragment of unmatched code points becomes one `unknown` word when it has ≥ 2 code points (a single leftover
code point can never be indexed and is ignored). Both lists keep their first occurrence order, without duplicates.
No pythainlp at query time.

Shards: an index shard holds the tokens with fnv1a32(token) % search.index_shards == shard (FNV-1a 32-bit over the
UTF-8 bytes); a doc shard holds ordinals [shard · docs_per_shard, (shard + 1) · docs_per_shard).

  20_docs              ordinal, article_id, title_th, title_en, year, journal_index, topic_id (−1 = unassigned),
                       doi, url — no author, no abstract
  20_postings          token, ordinal — unique pairs sorted by (token, ordinal); tokens of the vocabulary only
  20_galaxy_points     ordinal, x, y (0…65535 over the map view box, −1 = no coordinate), topic_id, year
  20_search_meta.json  n_docs, window, journals, years, search {published, skipped, …}, galaxy {published, skipped,
                       bounds, placed}
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from functools import lru_cache
from itertools import chain
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.checkpoints import analysed_window, article_topics
from atlas.io_utils import read_table, write_table

TOKENIZER_VERSION = 1
FIELDS = ("title_th", "title_en", "keywords_th", "keywords_en")
QUANT = 65535                                     # galaxy coordinates are integers 0…QUANT over the view box
FNV_OFFSET, FNV_PRIME = 0x811C9DC5, 0x01000193

EN_STOPWORDS = frozenset(
    "an and are as at be by for from has have in into is it its of on or that the their this to toward towards "
    "via vs was were which with".split())
TH_STOPWORDS = frozenset([
    "\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI EK}",
    "\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER SARA A}",
    "\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU}",
    "\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER NO NU}",
    "\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER RO RUA}",
    "\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER MO MA}",
    "\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}",
    "\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER BO BAIMAI}",
    "\N{THAI CHARACTER SARA E}\N{THAI CHARACTER PHO PHAN}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}"
    "\N{THAI CHARACTER O ANG}",
    "\N{THAI CHARACTER SARA O}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER YO YAK}",
    "\N{THAI CHARACTER CHO CHAN}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER KO KAI}",
    "\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MAI THO}",
    "\N{THAI CHARACTER SO SO}\N{THAI CHARACTER SARA UE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NGO NGU}",
    "\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER O ANG}",
    "\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI EK}",
    "\N{THAI CHARACTER SARA E}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER MAITAIKHU}\N{THAI CHARACTER NO NU}",
    "\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA II}",
    "\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER MAI THO}",
    "\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AA}",
    "\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER YO YAK}",
    "\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NGO NGU}",
    "\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER MO MA}",
    "\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA A}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER WO WAEN}"
    "\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NGO NGU}",
    "\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI THO}",
    "\N{THAI CHARACTER NO NU}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER NO NU}",
    "\N{THAI CHARACTER O ANG}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AA}"
    "\N{THAI CHARACTER NGO NGU}",
    "\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER MAI EK}",
])
STOPWORDS = EN_STOPWORDS | TH_STOPWORDS

_THAI_CLASS = ("\N{THAI CHARACTER KO KAI}-\N{THAI CHARACTER HO NOKHUK}"
               "\N{THAI CHARACTER SARA A}-\N{THAI CHARACTER PHINTHU}"
               "\N{THAI CHARACTER SARA E}-\N{THAI CHARACTER LAKKHANGYAO}"
               "\N{THAI CHARACTER MAITAIKHU}-\N{THAI CHARACTER YAMAKKAN}")
_RUNS = re.compile(f"([{_THAI_CLASS}]+)|([^\\W_{chr(0x0E00)}-{chr(0x0E7F)}]+)")
_THAI_DIGITS = str.maketrans({chr(0x0E50 + i): str(i) for i in range(10)})
_NIKHAHIT_SARA_AA = "\N{THAI CHARACTER NIKHAHIT}\N{THAI CHARACTER SARA AA}"


def normalise(text: str) -> str:
    """NFC, NIKHAHIT + SARA AA → SARA AM, lower case, Thai digits → ASCII digits (index and query alike)."""
    s = unicodedata.normalize("NFC", text or "").replace(_NIKHAHIT_SARA_AA, "\N{THAI CHARACTER SARA AM}")
    return s.lower().translate(_THAI_DIGITS)


def runs(text: str) -> list[tuple[bool, str]]:
    """[(is_thai, run)] of the normalised text, in order."""
    return [(bool(m.group(1)), m.group(0)) for m in _RUNS.finditer(normalise(text))]


def keep_word(tok: str) -> bool:
    """The filter every token passes: ≥ 2 code points, not a stopword, digits only when 4 of them (a year)."""
    return len(tok) >= 2 and tok not in STOPWORDS and (not tok.isdecimal() or len(tok) == 4)


@lru_cache(maxsize=1 << 18)
def _thai_words(run: str) -> tuple[str, ...]:
    from pythainlp.tokenize import word_tokenize

    return tuple(w for w in word_tokenize(run, engine="newmm", keep_whitespace=False) if keep_word(w))


def tokens(text: str) -> list[str]:
    """Index tokens of one text, in order (duplicates kept)."""
    out: list[str] = []
    for thai, run in runs(text):
        if thai:
            out.extend(_thai_words(run))
        elif keep_word(run):
            out.append(run)
    return out


def query_tokens(q: str, vocab: set[str] | frozenset[str], max_chars: int) -> tuple[list[str], list[str]]:
    """(known, unknown) words of a search query — greedy longest match against the vocabulary for Thai runs."""
    known: list[str] = []
    unknown: list[str] = []

    def add(bucket: list[str], w: str) -> None:
        if w not in bucket:
            bucket.append(w)

    for thai, run in runs(q):
        if not thai:
            if keep_word(run):
                add(known if run in vocab else unknown, run)
            continue
        i, pending, n = 0, -1, len(run)
        while i < n:
            hit = ""
            for length in range(min(max_chars, n - i), 1, -1):
                w = run[i:i + length]
                if w in vocab or w in STOPWORDS:
                    hit = w
                    break
            if not hit:
                pending = i if pending < 0 else pending
                i += 1
                continue
            if pending >= 0 and i - pending >= 2:
                add(unknown, run[pending:i])
            pending = -1
            if hit not in STOPWORDS:
                add(known, hit)
            i += len(hit)
        if pending >= 0 and n - pending >= 2:
            add(unknown, run[pending:])
    return known, unknown


def fnv1a32(s: str) -> int:
    """FNV-1a 32-bit hash of the UTF-8 bytes of s."""
    h = FNV_OFFSET
    for b in s.encode("utf-8"):
        h = ((h ^ b) * FNV_PRIME) & 0xFFFFFFFF
    return h


def _text(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].fillna("").astype(str) if col in df.columns else pd.Series("", index=df.index, dtype=str)


def doc_order(work: str | Path) -> pd.DataFrame:
    """ordinal, article_id, year, journal_name, doi, url + the indexed fields — the published articles in
    article_id order (dated in the analysed window, with a Thai or English title)."""
    work = Path(work)
    arts = read_table(work / "01_articles.parquet", ["article_id", "year", *FIELDS, "journal_name", "doi", "url"])
    out = pd.DataFrame({"article_id": arts["article_id"].astype(str),
                        "year": pd.to_numeric(arts["year"], errors="coerce")})
    for col in (*FIELDS, "journal_name", "doi", "url"):
        out[col] = _text(arts, col).str.strip()
    keep = out["year"].notna() & ((out["title_th"] != "") | (out["title_en"] != ""))
    win = analysed_window(work)
    if win:
        keep &= out["year"].between(*win)
    out = out[keep].sort_values("article_id", kind="stable").drop_duplicates("article_id").reset_index(drop=True)
    out["year"] = out["year"].astype(int)
    out.insert(0, "ordinal", np.arange(len(out), dtype=np.int64))
    return out


def build_postings(docs: pd.DataFrame, max_token_chars: int, min_df: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(postings [token, ordinal] unique and sorted, vocab [token, df] sorted) of `docs` (ordinal + FIELDS)."""
    text = _text(docs, FIELDS[0])
    for col in FIELDS[1:]:
        text = text + "\n" + _text(docs, col)
    toks = [tokens(t) for t in text]                 # the only per-article loop: tokenisation (Thai runs cached)
    lens = np.fromiter((len(t) for t in toks), dtype=np.int64, count=len(toks))
    p = pd.DataFrame({"token": pd.Series(list(chain.from_iterable(toks)), dtype=str),
                      "ordinal": np.repeat(docs["ordinal"].to_numpy(dtype=np.int64), lens)})
    p = p[p["token"].str.len() <= max_token_chars].drop_duplicates()
    df = p.groupby("token").size()
    df = df[df >= min_df]
    p = p[p["token"].isin(df.index)].sort_values(["token", "ordinal"], kind="stable").reset_index(drop=True)
    vocab = df.rename("df").rename_axis("token").reset_index().sort_values("token", kind="stable")
    return p, vocab.reset_index(drop=True)


def galaxy_points(docs: pd.DataFrame, galaxy: pd.DataFrame, topic_of: pd.Series,
                  bounds: tuple[float, float, float, float]) -> pd.DataFrame:
    """ordinal, x, y, topic_id, year — coordinates quantised to 0…QUANT over `bounds` (x0, y0, x1, y1); −1 where
    an article has no galaxy coordinate."""
    x0, y0, x1, y1 = bounds
    g = galaxy.assign(article_id=galaxy["article_id"].astype(str)).drop_duplicates("article_id").set_index(
        "article_id")
    ids = docs["article_id"].astype(str)
    gx = pd.to_numeric(ids.map(g["gx"]), errors="coerce").to_numpy(dtype=float)
    gy = pd.to_numeric(ids.map(g["gy"]), errors="coerce").to_numpy(dtype=float)

    def quant(v: np.ndarray, lo: float, hi: float) -> np.ndarray:
        q = np.clip(np.rint((v - lo) / (hi - lo) * QUANT), 0, QUANT)
        return np.where(np.isfinite(v), q, -1).astype(np.int64)

    return pd.DataFrame({"ordinal": docs["ordinal"].to_numpy(dtype=np.int64), "x": quant(gx, x0, x1),
                         "y": quant(gy, y0, y1),
                         "topic_id": ids.map(topic_of).fillna(-1).astype(np.int64).to_numpy(),
                         "year": docs["year"].to_numpy(dtype=np.int64)})


def _topics(work: Path) -> pd.Series:
    try:
        return article_topics(work)
    except FileNotFoundError:
        return pd.Series(dtype=np.int64)


def search(cfg: dict) -> dict:
    work = Path(cfg["pipeline"]["work_dir"])
    scfg = cfg["search"]
    for stale in work.glob("20_*"):          # a re-run that stops half-way must not leave the old release's tables
        stale.unlink()
    meta_path = work / "20_search_meta.json"
    if not scfg["enabled"]:
        why = "search.enabled is false"
        meta = {"search": {"published": False, "skipped": why},
                "galaxy": {"published": False, "skipped": f"{why} (galaxy cards read the search doc store)"}}
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        print(f"[search] {why} — no search index and no galaxy")
        return meta
    t0 = time.time()
    docs = doc_order(work)
    topic_of = _topics(work)
    journals = sorted(set(docs["journal_name"]))
    jindex = {j: i for i, j in enumerate(journals)}
    out = docs[["ordinal", "article_id", "title_th", "title_en", "year"]].assign(
        journal_index=docs["journal_name"].map(jindex).astype(np.int64),
        topic_id=docs["article_id"].map(topic_of).fillna(-1).astype(np.int64), doi=docs["doi"], url=docs["url"])
    postings, vocab = build_postings(docs, int(scfg["max_token_chars"]), int(scfg["min_df"]))
    write_table(out, work / "20_docs.parquet")
    write_table(postings, work / "20_postings.parquet")
    t_index = time.time() - t0

    lcfg = cfg["layout"]
    bounds = (0.0, 0.0, float(lcfg["view_w"]), float(lcfg["view_h"]))
    gal_path = work / "09_galaxy.parquet"
    if not lcfg["galaxy"]:
        gal = {"published": False, "skipped": "layout.galaxy is false"}
    elif not gal_path.exists():
        gal = {"published": False, "skipped": "work/09_galaxy is missing (run the layout step)"}
    else:
        pts = galaxy_points(docs, read_table(gal_path), topic_of, bounds)
        write_table(pts, work / "20_galaxy_points.parquet")
        gal = {"published": True, "skipped": None, "bounds": list(bounds), "placed": int((pts["x"] >= 0).sum())}
    win = analysed_window(work)
    meta = {"n_docs": len(docs), "window": list(win) if win else None, "journals": journals,
            "years": sorted({int(y) for y in docs["year"]}),
            "search": {"published": True, "skipped": None, "tokenizer_version": TOKENIZER_VERSION,
                       "n_tokens": len(vocab), "n_postings": len(postings)},
            "galaxy": gal}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    n_shards, per = int(scfg["index_shards"]), int(scfg["docs_per_shard"])
    shard_sizes = np.bincount(np.array([fnv1a32(t) % n_shards for t in vocab["token"]], dtype=np.int64),
                              minlength=n_shards)
    print(f"[search] {len(docs):,} articles, {len(vocab):,} tokens, {len(postings):,} postings in {t_index:.1f}s — "
          f"{n_shards} index shards ({int(shard_sizes.min()) if len(vocab) else 0}–"
          f"{int(shard_sizes.max()) if len(vocab) else 0} tokens each), {-(-len(docs) // per)} doc shards of ≤ {per:,}"
          + (f"; galaxy: {gal['placed']:,} placed" if gal["published"] else f"; galaxy skipped: {gal['skipped']}"))
    return meta
