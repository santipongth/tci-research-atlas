"""'Match my abstract' (R3) and 'where to publish' (R4): the index the browser matches a pasted abstract against.

The browser never downloads a model and never sends the text anywhere: web/src/lib/matcher.ts folds the text,
cuts it into the same character trigrams, weights them with the published idf and ranks topics by cosine
similarity; journals are ranked by how much of their recent output falls in the closest topics.

Analyzer — identical in Python and TypeScript (tests/fixtures/match_parity.json pins both):
  fold   NFC → join a decomposed sara am → drop zero-width characters and soft hyphens → NFD → drop Latin
         combining accents (U+0300–U+036F) → drop Thai marks U+0E47–U+0E4C → lower case → collapse whitespace
         (exactly JavaScript's whitespace class, not Python's) to one space, trim (= web/src/lib/search.ts foldText)
  grams  every space-separated word padded with one space on each side, then every 3-character slice
         (a padded word shorter than 3 characters is one gram) — the char_wb (3, 3) analyzer of scikit-learn;
         characters are code points: the web must slice Array.from(word), never UTF-16 units (astral emoji)
Topic vectors: up to match.docs_per_topic articles per topic (seeded sample) → gram counts summed per topic →
(1 + ln tf) · idf, idf = ln((1 + N) / (1 + df)) + 1 over the sampled articles (grams in < min_df articles are
dropped) → L2-normalised → the max_terms heaviest grams kept and renormalised. max_terms shrinks (×0.8, not
below min_terms) until the file fits match.max_bytes. Only grams, idf and weights are published — no text.

Step `match` (after journals) → work/14_match.json (internal topic ids and journal keys; export maps them).
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import normalize

from atlas.io_utils import read_table

ANALYZER = "char_wb3"
FOLD_VERSION = "atlas-fold-1"
N = 3
_DECOMPOSED_AM = "\N{THAI CHARACTER NIKHAHIT}\N{THAI CHARACTER SARA AA}"
_INVISIBLE = re.compile(f"[{chr(0x200B)}-{chr(0x200D)}{chr(0xFEFF)}{chr(0x00AD)}]")
_LATIN_ACCENTS = re.compile(f"[{chr(0x0300)}-{chr(0x036F)}]")
_THAI_ABOVE = re.compile(f"[{chr(0x0E47)}-{chr(0x0E4C)}]")
# exactly the JavaScript \s class (web foldText uses /\s+/g): Python's \s also takes U+001C–U+001F and U+0085
_JS_SPACE = "".join(chr(c) for c in (0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20, 0xA0, 0x1680, *range(0x2000, 0x200B), 0x2028,
                                     0x2029, 0x202F, 0x205F, 0x3000, 0xFEFF))
_SPACES = re.compile(f"[{re.escape(_JS_SPACE)}]+")
TEXT_COLUMNS = ("title_th", "title_en", "keywords_th", "keywords_en")
ABSTRACT_COLUMNS = ("abstract_th", "abstract_en")
OUT = "14_match.json"


def match_fold(text: str | None) -> str:
    s = unicodedata.normalize("NFC", text or "").replace(_DECOMPOSED_AM, "\N{THAI CHARACTER SARA AM}")
    s = unicodedata.normalize("NFD", _INVISIBLE.sub("", s))
    s = _THAI_ABOVE.sub("", _LATIN_ACCENTS.sub("", s)).lower()
    return _SPACES.sub(" ", s).strip()


def char_grams(folded: str, n: int = N) -> list[str]:
    out: list[str] = []
    for word in folded.split(" ") if folded else []:
        w = f" {word} "
        if len(w) <= n:
            out.append(w)
        else:
            out.extend(w[i:i + n] for i in range(len(w) - n + 1))
    return out


def analyze(text: str) -> list[str]:
    return char_grams(match_fold(text))


def doc_text(row: dict, abstract_chars: int) -> str:
    parts = [str(row.get(c) or "") for c in TEXT_COLUMNS]
    parts += [str(row.get(c) or "")[:abstract_chars] for c in ABSTRACT_COLUMNS]
    return " ".join(p for p in parts if p)


def sample_members(topic_of: pd.Series, per_topic: int, seed: int) -> pd.Series:
    """article_id → topic for at most per_topic articles of each topic (seeded, independent of row order)."""
    keep = []
    for tid, ids in topic_of.groupby(topic_of).groups.items():
        ids = sorted(ids)
        if len(ids) > per_topic:
            pick = np.random.default_rng(seed + int(tid)).choice(len(ids), per_topic, replace=False)
            ids = [ids[i] for i in sorted(pick)]
        keep += ids
    return topic_of.loc[sorted(keep)]


def topic_vectors(texts: list[str], topics: np.ndarray, min_df: int) -> tuple[list[str], np.ndarray, list[int],
                                                                             sparse.csr_matrix]:
    """(grams, idf, topic ids, L2-normalised topic × gram matrix)."""
    vec = CountVectorizer(analyzer=analyze, min_df=min_df, dtype=np.float64)
    try:
        X = vec.fit_transform(texts)
    except ValueError:                             # no gram survives min_df
        return [], np.zeros(0), [], sparse.csr_matrix((0, 0))
    grams = vec.get_feature_names_out().tolist()
    df = np.asarray((X > 0).sum(axis=0)).ravel()
    idf = np.log((1 + X.shape[0]) / (1 + df)) + 1.0
    tids = sorted(set(int(t) for t in topics))
    row = {t: i for i, t in enumerate(tids)}
    T = sparse.csr_matrix((np.ones(len(topics)), ([row[int(t)] for t in topics], np.arange(len(topics)))),
                          shape=(len(tids), X.shape[0]))
    tf = (T @ X).tocsr()
    tf.data = 1.0 + np.log(tf.data)
    W = normalize(tf.multiply(idf).tocsr(), norm="l2", axis=1)
    return grams, idf, tids, W.tocsr()


def truncate(W: sparse.csr_matrix, k: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """Per row: (gram indices, weights) of the k heaviest grams, renormalised to unit length."""
    out = []
    for i in range(W.shape[0]):
        lo, hi = W.indptr[i], W.indptr[i + 1]
        idx, val = W.indices[lo:hi], W.data[lo:hi]
        order = np.lexsort((idx, -val))[:k]
        idx, val = idx[order], val[order]
        norm = float(np.sqrt((val ** 2).sum()))
        out.append((idx, val / norm if norm else val))
    return out


def build_index(grams: list[str], idf: np.ndarray, tids: list[int], W: sparse.csr_matrix,
                journals: list[dict], mcfg: dict, n_docs: int) -> dict:
    """The published index (internal ids) — max_terms shrinks until the JSON (its "bytes" key included) fits
    match.max_bytes. A topic left without any gram (all below min_df) is not in the index."""
    k = int(mcfg["max_terms"])
    while True:
        kept = [(t, r) for t, r in zip(tids, truncate(W, k)) if len(r[0])]
        rows = [r for _, r in kept]
        used = sorted({int(i) for idx, _ in rows for i in idx})
        pos = {g: p for p, g in enumerate(used)}
        index = {
            "analyzer": ANALYZER, "fold": FOLD_VERSION, "docs": int(n_docs), "max_terms": k,
            "min_similarity": float(mcfg["min_similarity"]), "fit_topics": int(mcfg["fit_topics"]),
            "min_query_chars": int(mcfg["min_query_chars"]),
            "grams": [grams[i] for i in used], "idf": [round(float(idf[i]), 4) for i in used],
            "topics": [{"topic_id": t, "terms": [pos[int(i)] for i in idx], "weights": [round(float(v), 4) for v in val]}
                       for t, (idx, val) in kept],
            "journals": journals,
            "bytes": 0,
        }
        size = 0
        while True:                                # the size of the file that holds its own size (a fixpoint)
            index["bytes"] = size
            measured = len(json.dumps(index, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            if measured == size:
                break
            size = measured
        if size <= int(mcfg["max_bytes"]) or k <= int(mcfg["min_terms"]):
            if size > int(mcfg["max_bytes"]):
                print(f"[match] WARNING: index is {size:,} bytes > match.max_bytes even at min_terms={k}")
            return index
        k = max(int(mcfg["min_terms"]), int(k * 0.8))


def journal_mixes(work: Path, mcfg: dict) -> list[dict]:
    """[{journal_key, topics, shares}] for active journals with enough articles (13_journals) — R4."""
    try:
        summary = read_table(work / "13_journals.parquet")
        mix = read_table(work / "13_journal_topics.parquet")
    except FileNotFoundError:
        return []
    ok = set(summary.loc[summary["active"].astype(bool) & ~summary["low_data"].astype(bool), "journal_key"])
    m = mix[mix["journal_key"].isin(ok) & (mix["share"] >= float(mcfg["journal_min_share"]))]
    out = []
    for jk, g in m.groupby("journal_key"):
        g = g.sort_values(["share", "topic_id"], ascending=[False, True]).head(int(mcfg["journal_topics"]))
        out.append({"journal_key": jk, "topics": [int(t) for t in g["topic_id"]],
                    "shares": [round(float(s), 4) for s in g["share"]]})
    return out


def match(cfg: dict) -> dict:
    work = Path(cfg["pipeline"]["work_dir"])
    mcfg = cfg["match"]
    (work / OUT).unlink(missing_ok=True)
    if not mcfg["enabled"]:
        print("[match] match.enabled is false — skipped (no match index in this release)")
        return {}
    docs = read_table(work / "02_docs.parquet")
    fine = read_table(work / "04_fine_topics.parquet")[["article_id", "fine_topic"]]
    d = docs.merge(fine, on="article_id")
    d = d[d["fine_topic"] >= 0]
    topic_of = d.set_index("article_id")["fine_topic"].astype(int)
    picked = sample_members(topic_of, int(mcfg["docs_per_topic"]), int(cfg["pipeline"]["seed"]))
    rows = d.set_index("article_id").loc[picked.index]
    texts = [doc_text(r, int(mcfg["abstract_chars"])) for r in rows.to_dict("records")]
    grams, idf, tids, W = topic_vectors(texts, picked.to_numpy(), int(mcfg["min_df"]))
    index = build_index(grams, idf, tids, W, journal_mixes(work, mcfg), mcfg, len(texts))
    (work / OUT).write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[match] {len(index['topics'])} topic vectors × ≤ {index['max_terms']} trigrams "
          f"({len(index['grams']):,} distinct), {len(index['journals'])} journals, {index['bytes'] / 1e6:.2f} MB")
    return index


# Inputs whose fold + grams are pinned in tests/fixtures/match_parity.json (scripts/write_match_parity.py) and
# checked by both test suites — Thai tone marks, a decomposed sara am, accents, zero-width space, odd spacing.
PARITY_CASES: tuple[str, ...] = (
    "ความต้องการของผู้สูงอายุในชุมชน",
    "การท" + _DECOMPOSED_AM + "งานเป็นทีม",
    "Café   Naïve  AI-based  Learning",
    "แชต" + chr(0x200B) + "บอต" + chr(0x00AD) + "ในห้องเรียน",
    "line1\nline2\tx  ",
    "การตลาดดิจิทัล (Digital Marketing) 2024",
    "a b ab",
    "",
    "ข้อความ" + chr(0xA0) + "ทดสอบ" + chr(0x3000) + "AI" + chr(0x2009) + "x",    # NBSP, ideographic + thin space
    "a" + chr(0x1C) + "b" + chr(0x85) + "c" + chr(0x0B) + "d" + chr(0x07) + "e",    # controls: only VT is JS whitespace
    "AI " + chr(0x1F600) + " แชตบอต" + chr(0x1F600) + "x",                         # astral: slice by code point
)
