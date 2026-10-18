"""Class-based TF-IDF (c-TF-IDF, Grootendorst 2022) over pre-tokenised documents.

score(t, c) = tf(t, c) · log(1 + A / f(t))
  tf(t, c) = count of t in class c / total tokens in c
  A        = average tokens per class
  f(t)     = count of t over all classes
Words come from pythainlp tokenisation (real Thai words, not char n-gram fragments);
author keywords are scored as whole phrases.
"""
from __future__ import annotations

from collections import Counter

import numpy as np

from atlas.thai import tokenize


def ctfidf_top_terms(class_tokens: dict[int, list[list[str]]], top_n: int) -> dict[int, list[str]]:
    counts = {c: Counter(tok for doc in docs for tok in doc) for c, docs in class_tokens.items()}
    freq: Counter = Counter()
    for cnt in counts.values():
        freq.update(cnt)
    totals = {c: sum(cnt.values()) for c, cnt in counts.items()}
    nonempty = [v for v in totals.values() if v]
    avg = sum(nonempty) / len(nonempty) if nonempty else 0.0
    out: dict[int, list[str]] = {}
    for c, cnt in counts.items():
        if not totals[c]:
            out[c] = []
            continue
        scores = {t: (n / totals[c]) * np.log(1 + avg / freq[t]) for t, n in cnt.items()}
        out[c] = [t for t, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]]
    return out


def topic_terms(texts_by_topic: dict[int, list[str]], top_n: int, max_docs: int, seed: int) -> dict[int, list[str]]:
    rng = np.random.default_rng(seed)
    toks: dict[int, list[list[str]]] = {}
    for t, docs in texts_by_topic.items():
        if len(docs) > max_docs:
            docs = [docs[i] for i in sorted(rng.choice(len(docs), max_docs, replace=False))]
        toks[t] = [tokenize(d) for d in docs]
    return ctfidf_top_terms(toks, top_n)


def topic_keywords(keywords_by_topic: dict[int, list[str]], top_n: int) -> dict[int, list[str]]:
    toks = {t: [[k.strip() for k in s.split(";") if k.strip()] for s in kws] for t, kws in keywords_by_topic.items()}
    return ctfidf_top_terms(toks, top_n)
