"""Research methods (E11, D7) — a TH/EN lexicon + a sample-size reader → topic / journal / corpus aggregates.

Every article's title + abstract (TH and EN) is read internally; only aggregates are published (share of the
articles that name a method, median sample size). Text and patterns are folded the same way — Thai tone marks
dropped (atlas.thai.fold_thai), lower case — so text whose marks were lost in PDF conversion still matches.
An article may use several methods; shares are over the articles in which at least one method was found
("coverage" = that share of all articles). "Monoculture" (E11) = the share of those articles whose methods all
lie in methods.monoculture_methods (default: questionnaire + descriptive statistics only).

Step `methods` (after layout) writes work/12_methods_articles (article_id, year, topic_id, methods, sample_size),
12_methods_topics (one row per topic with ≥ methods.min_articles window articles) and 12_methods_meta.json
(lexicon version, window, corpus shares, shares by year).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.thai import clean_text, fold_thai


@dataclass(frozen=True)
class Method:
    key: str
    th: str
    en: str
    patterns: tuple[str, ...]          # lower-case regex parts; Thai written with marks, folded at compile time


METHODS: tuple[Method, ...] = (
    Method("survey", "แบบสอบถาม/การสำรวจ", "Questionnaire / survey",
           (r"แบบสอบถาม", r"การสำรวจ", r"questionnaire", r"\bsurveys?\b")),
    Method("interview", "การสัมภาษณ์", "Interviews", (r"สัมภาษณ์", r"\binterview")),
    Method("focus_group", "การสนทนากลุ่ม", "Focus groups", (r"สนทนากลุ่ม", r"focus groups?")),
    Method("experiment", "การทดลอง/กึ่งทดลอง", "Experiment / quasi-experiment",
           (r"กึ่งทดลอง", r"การวิจัยเชิงทดลอง", r"แบบแผนการทดลอง", r"quasi[- ]?experiment",
            r"\bexperimental (?:design|study|research|group)", r"randomi[sz]ed controlled", r"\brct\b")),
    Method("qualitative", "การวิจัยเชิงคุณภาพ", "Qualitative research", (r"เชิงคุณภาพ", r"\bqualitative\b")),
    Method("mixed", "การวิจัยแบบผสานวิธี", "Mixed methods", (r"ผสานวิธี", r"วิธีวิจัยแบบผสม", r"mixed[- ]methods?")),
    Method("rnd", "การวิจัยและพัฒนา", "Research and development", (r"การวิจัยและพัฒนา", r"research and development")),
    Method("action", "การวิจัยเชิงปฏิบัติการ", "Action research",
           (r"วิจัยเชิงปฏิบัติการ", r"action research", r"\bpar\b")),
    Method("case_study", "กรณีศึกษา", "Case study", (r"กรณีศึกษา", r"case stud(?:y|ies)")),
    Method("document", "การวิเคราะห์เอกสาร/เนื้อหา", "Document / content analysis",
           (r"วิเคราะห์เอกสาร", r"วิเคราะห์เนื้อหา", r"การวิจัยเอกสาร", r"documentary research",
            r"document analysis", r"content analysis")),
    Method("review", "การทบทวนอย่างเป็นระบบ/อภิมาน", "Systematic review / meta-analysis",
           (r"ทบทวนวรรณกรรมอย่างเป็นระบบ", r"การทบทวนอย่างเป็นระบบ", r"อภิมาน", r"systematic review",
            r"meta[- ]analys", r"scoping review")),
    Method("descriptive_stats", "สถิติเชิงพรรณนา", "Descriptive statistics",
           (r"ค่าเฉลี่ย", r"ร้อยละ", r"ส่วนเบี่ยงเบนมาตรฐาน", r"สถิติเชิงพรรณนา", r"descriptive statistic",
            r"\bpercentages?\b", r"standard deviation", r"\bmeans?\b")),
    Method("inferential", "สถิติเชิงอนุมาน", "Inferential statistics",
           (r"\bt[- ]?test", r"\banova\b", r"ความแปรปรวน", r"chi[- ]square", r"ไคสแควร์", r"สหสัมพันธ์",
            r"\bcorrelation", r"ถดถอย", r"\bregression")),
    Method("sem", "สมการโครงสร้าง/องค์ประกอบ", "SEM / factor analysis",
           (r"สมการโครงสร้าง", r"structural equation", r"\bsem\b", r"องค์ประกอบเชิงยืนยัน", r"confirmatory factor",
            r"\bcfa\b", r"pls[- ]sem")),
    Method("ml", "การเรียนรู้ของเครื่อง", "Machine learning",
           (r"การเรียนรู้ของเครื่อง", r"การเรียนรู้เชิงลึก", r"โครงข่ายประสาท", r"machine learning",
            r"deep learning", r"neural networks?")),
    Method("lab", "การทดลองในห้องปฏิบัติการ", "Laboratory study", (r"ห้องปฏิบัติการ", r"in vitro", r"\blaborator")),
)
METHOD_KEYS: tuple[str, ...] = tuple(m.key for m in METHODS)
LEXICON_VERSION = hashlib.sha1(json.dumps([[m.key, list(m.patterns)] for m in METHODS],
                                          ensure_ascii=False).encode("utf-8")).hexdigest()[:8]
_RX = {m.key: re.compile("|".join(f"(?:{fold_thai(p)})" for p in m.patterns)) for m in METHODS}

_NUM = r"(\d{1,3}(?:,\d{3})+|\d+)"
_SAMPLE_PATTERNS: tuple[tuple[re.Pattern, bool], ...] = (     # (pattern, has a unit → no year check)
    (re.compile(fold_thai(r"(?:กลุ่มตัวอย่าง|ผู้ตอบแบบสอบถาม|ผู้ให้ข้อมูลสำคัญ|ผู้ให้ข้อมูล|ผู้เข้าร่วม(?:การ)?วิจัย)"
                          r"[^0-9]{0,40}?") + _NUM + fold_thai(r"\s*(?:คน|ราย|ครัวเรือน|ตัวอย่าง|แห่ง|โรงเรียน|ชุด)")),
     True),
    (re.compile(r"\bn\s*=\s*" + _NUM + r"\b"), True),
    (re.compile(_NUM + r"\s+(?:respondents|participants|informants|students|teachers|nurses|patients|farmers|"
                       r"households|employees|subjects|samples|consumers|tourists)\b"), True),
    (re.compile(r"\b(?:sample(?: size)?|respondents|participants)\b[^0-9.;]{0,30}?" + _NUM + r"\b"), False),
)
TEXT_COLUMNS = ("title_th", "title_en", "keywords_th", "keywords_en", "abstract_th", "abstract_en")
ARTICLE_COLUMNS = ["article_id", "year", "topic_id", "methods", "sample_size"]


def fold(text: str | None) -> str:
    return fold_thai(clean_text(text)).lower()


def detect_methods(text: str | None) -> list[str]:
    t = fold(text)
    return [k for k, rx in _RX.items() if rx.search(t)]


def sample_size(text: str | None, max_size: int = 1_000_000) -> int | None:
    """The first plausible sample size in the text: '...กลุ่มตัวอย่าง จำนวน 400 คน', 'n = 400', '400 respondents',
    'a sample of 400'. A number without a unit that looks like a year (1900–2100, 2400–2600 BE) is skipped."""
    t = fold(text)
    cands = []
    for rx, has_unit in _SAMPLE_PATTERNS:
        for m in rx.finditer(t):
            n = int(m.group(1).replace(",", ""))
            if not has_unit and (1900 <= n <= 2100 or 2400 <= n <= 2600):
                continue
            if 2 <= n <= max_size:
                cands.append((m.start(), n))
    return min(cands)[1] if cands else None


def article_methods(docs: pd.DataFrame, max_sample: int) -> pd.DataFrame:
    """article_id, methods ("survey; inferential" — lexicon order), sample_size (nullable Int64)."""
    cols = [docs[c].fillna("").astype(str) for c in TEXT_COLUMNS if c in docs.columns]
    texts = [" . ".join(v) for v in zip(*cols)] if cols else [""] * len(docs)
    return pd.DataFrame({
        "article_id": docs["article_id"].to_numpy(),
        "methods": ["; ".join(detect_methods(t)) for t in texts],
        "sample_size": pd.array([sample_size(t, max_sample) for t in texts], dtype="Int64"),
    })


def _sets(methods: pd.Series) -> list[set[str]]:
    return [set(x for x in str(m).split("; ") if x) for m in methods.fillna("")]


def shares_of(methods: pd.Series) -> tuple[dict[str, int], int]:
    """({method: articles naming it}, articles naming at least one method) — methods in lexicon order."""
    sets = [s for s in _sets(methods) if s]
    return {k: sum(k in s for s in sets) for k in METHOD_KEYS if any(k in s for s in sets)}, len(sets)


def monoculture_share(methods: pd.Series, mono: list[str]) -> float | None:
    sets = [s for s in _sets(methods) if s]
    return sum(s <= set(mono) for s in sets) / len(sets) if sets else None


def in_window(year: pd.Series, start: int, end: int) -> pd.Series:
    """Boolean mask of years in [start, end]; a missing year is outside."""
    return pd.to_numeric(year, errors="coerce").between(start, end).fillna(False).astype(bool)


def summarise_topics(am: pd.DataFrame, start: int, end: int, mcfg: dict) -> pd.DataFrame:
    """One row per topic with ≥ min_articles articles in [start, end]: articles, with_methods, coverage,
    counts (JSON {method: n}), sample-size n/median/q1/q3, monoculture_share, monoculture."""
    w = am[(am["topic_id"] >= 0) & in_window(am["year"], start, end)]
    rows = []
    for tid, g in w.groupby("topic_id"):
        if len(g) < int(mcfg["min_articles"]):
            continue
        counts, n_with = shares_of(g["methods"])
        ss = g["sample_size"].dropna().astype(float).to_numpy()
        mono = monoculture_share(g["methods"], mcfg["monoculture_methods"])
        rows.append({
            "topic_id": int(tid), "articles": int(len(g)), "with_methods": int(n_with),
            "coverage": n_with / len(g), "counts": json.dumps(counts),
            "ss_n": int(len(ss)), "ss_median": float(np.median(ss)) if len(ss) else np.nan,
            "ss_q1": float(np.percentile(ss, 25)) if len(ss) else np.nan,
            "ss_q3": float(np.percentile(ss, 75)) if len(ss) else np.nan,
            "monoculture_share": mono if mono is not None else np.nan,
            "monoculture": bool(mono is not None and mono >= float(mcfg["monoculture_min_share"])),
        })
    cols = ["topic_id", "articles", "with_methods", "coverage", "counts", "ss_n", "ss_median", "ss_q1", "ss_q3",
            "monoculture_share", "monoculture"]
    return pd.DataFrame(rows, columns=cols)


def by_year(am: pd.DataFrame, years: list[int]) -> dict:
    """{years, articles: [n with ≥1 method], shares: {method: [share per year]}} over every dated article."""
    out = {"years": [int(y) for y in years], "articles": [], "shares": {k: [] for k in METHOD_KEYS}}
    for y in years:
        counts, n_with = shares_of(am.loc[in_window(am["year"], y, y), "methods"])
        out["articles"].append(int(n_with))
        for k in METHOD_KEYS:
            out["shares"][k].append(round(counts.get(k, 0) / n_with, 4) if n_with else 0.0)
    out["shares"] = {k: v for k, v in out["shares"].items() if any(v)}
    return out


OUT_FILES = ("12_methods_articles.parquet", "12_methods_topics.parquet", "12_methods_meta.json",
             "12_methods_notes.parquet")


def methods(cfg: dict, llm=None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    mcfg = cfg["methods"]
    for name in OUT_FILES:                     # a re-run (or methods.enabled: false) never leaves stale tables
        (work / name).unlink(missing_ok=True)
    if not mcfg["enabled"]:
        print("[methods] methods.enabled is false — skipped (no methods module in this release)")
        return pd.DataFrame(columns=ARTICLE_COLUMNS)
    docs = read_table(work / "02_docs.parquet")
    fine = read_table(work / "04_fine_topics.parquet")[["article_id", "fine_topic"]]
    meta6 = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    am = article_methods(docs, int(mcfg["max_sample_size"]))
    am = (am.merge(docs[["article_id", "year"]], on="article_id", how="left")
          .merge(fine.rename(columns={"fine_topic": "topic_id"}), on="article_id", how="left"))
    am["topic_id"] = am["topic_id"].fillna(-1).astype(int)
    am["year"] = pd.to_numeric(am["year"], errors="coerce").astype("Int64")
    am = am[ARTICLE_COLUMNS]
    write_table(am, work / "12_methods_articles.parquet")
    end = int(meta6["last_complete_year"])
    start = end - int(mcfg["window_years"]) + 1
    topics = summarise_topics(am, start, end, mcfg)
    write_table(topics, work / "12_methods_topics.parquet")
    win = am[in_window(am["year"], start, end)]
    counts, n_with = shares_of(win["methods"])
    meta = {"lexicon_version": LEXICON_VERSION, "window": [start, end], "articles": int(len(win)),
            "with_methods": int(n_with), "counts": counts,
            "monoculture_share": monoculture_share(win["methods"], mcfg["monoculture_methods"]),
            "by_year": by_year(am, [int(y) for y in meta6.get("years", [])])}
    (work / "12_methods_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    cov = n_with / len(win) if len(win) else 0.0
    print(f"[methods] lexicon {LEXICON_VERSION}: methods named in {cov:.0%} of {len(win):,} articles {start}–{end}; "
          f"{len(topics)} topics summarised ({int(topics['monoculture'].sum()) if len(topics) else 0} monoculture)")
    return am
