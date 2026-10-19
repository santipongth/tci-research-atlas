"""Research methods (E11, D7) — a TH/EN lexicon + a sample-size reader → topic / journal / corpus aggregates.

Every article's title + abstract (TH and EN) is read internally; only aggregates are published (share of the
articles that name a method, median sample size). Text and patterns are folded the same way — Thai tone marks
dropped (atlas.thai.fold_thai), lower case — so text whose marks were lost in PDF conversion still matches.
An article may use several methods; shares are over the articles in which at least one method was found
("coverage" = that share of all articles). "Monoculture" (E11) = the share of those articles whose methods all
lie in methods.monoculture_methods (default: questionnaire + descriptive statistics only).

Step `methods` (after layout) writes work/12_methods_articles (article_id, year, topic_id, methods, sample_size),
12_methods_topics (one row per topic with ≥ methods.min_articles window articles) and 12_methods_meta.json
(lexicon version, window, corpus shares, shares by year); with methods.provider: llm also 12_methods_notes
(method_notes — topic level only, grounded, template fallback).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, field_validator

from atlas.io_utils import read_table, write_table
from atlas.llm_runner import LlmItem, LlmJob, run_job
from atlas.prompts import load_prompt, prompt_version, render_prompt
from atlas.thai import clean_text, fold_thai


@dataclass(frozen=True)
class Method:
    key: str
    th: str
    en: str
    patterns: tuple[str, ...]          # lower-case regex parts; Thai written with marks, folded at compile time


# whole words: "productivity" (economics R&D) is not a product
_RND_TERMS = (r"(?:\bproducts?\b|new product|product development|\binnovat|\bprototyp|\bcurricul|"
              r"นวัตกรรม|ผลิตภัณฑ์|ต้นแบบ|หลักสูตร)")
_SEM_TOOLS = r"(?:amos|lisrel|smartpls|mplus|lavaan|rmsea|cfi)"     # SEM programs and fit indices
_ML_TERMS = r"(?:โครงข่ายประสาท|neural|model|โมเดล|อัลกอริทึม)"

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
    Method("rnd", "การวิจัยและพัฒนา", "Research and development",
           (r"การวิจัยและพัฒนา",       # "research and development" alone is also economics (R&D spending)
            rf"research and development(?=[\s\S]*{_RND_TERMS})", rf"{_RND_TERMS}[\s\S]*research and development")),
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
           (r"ค่าเฉลี่ย", r"ส่วนเบี่ยงเบนมาตรฐาน", r"สถิติเชิงพรรณนา", r"descriptive statistic",
            r"standard deviation",       # bare "mean(s)" / "percentage" / ร้อยละ are not method signals
            r"\bmean (?:score|value|age)s?\b", r"\bmean\s*[=±]", r"\(mean\b", r"\bsd\s*=")),
    Method("inferential", "สถิติเชิงอนุมาน", "Inferential statistics",
           (r"\bt[- ]?test", r"\banova\b", r"ความแปรปรวน", r"chi[- ]square", r"ไคสแควร์", r"สหสัมพันธ์",
            r"\bcorrelation", r"ถดถอย", r"\bregression")),
    Method("sem", "สมการโครงสร้าง/องค์ประกอบ", "SEM / factor analysis",
           (r"สมการโครงสร้าง", r"structural equation", r"องค์ประกอบเชิงยืนยัน", r"confirmatory factor",
            r"pls[- ]sem", r"\b(?:lisrel|smartpls)\b",
            # the bare acronyms SEM / CFA (scanning electron microscopy, ...) count only beside a SEM program
            rf"\b(?:sem|cfa)\b[\s\S]*\b{_SEM_TOOLS}\b", rf"\b{_SEM_TOOLS}\b[\s\S]*\b(?:sem|cfa)\b")),
    Method("ml", "การเรียนรู้ของเครื่อง", "Machine learning",
           (r"การเรียนรู้ของเครื่อง", r"โครงข่ายประสาท", r"machine learning", r"deep learning", r"neural networks?",
            # "deep learning" in pedagogy is not ML: the Thai phrase counts only beside a model / algorithm term
            rf"การเรียนรู้เชิงลึก[\s\S]*{_ML_TERMS}", rf"{_ML_TERMS}[\s\S]*การเรียนรู้เชิงลึก")),
    Method("lab", "การทดลองในห้องปฏิบัติการ", "Laboratory study", (r"ห้องปฏิบัติการ", r"in vitro", r"\blaborator")),
)
METHOD_KEYS: tuple[str, ...] = tuple(m.key for m in METHODS)
LEXICON_VERSION = hashlib.sha1(json.dumps([[m.key, list(m.patterns)] for m in METHODS],
                                          ensure_ascii=False).encode("utf-8")).hexdigest()[:8]
_RX = {m.key: re.compile("|".join(f"(?:{fold_thai(p)})" for p in m.patterns)) for m in METHODS}

_NUM = r"(?<![\d.,])(?P<num>\d{1,3}(?:,\d{3})+|\d+)(?!\d|[.,]\d)"        # "2.5" and "12,34" are not counts
_PERSON_UNITS = r"\s*(?:คน|ราย|ครัวเรือน|ตัวอย่าง)"                    # never แห่ง / โรงเรียน / ชุด (places, sets)
_SUBJECTS = ("นักเรียน|นักศึกษา|ผู้เรียน|ครู|อาจารย์|พยาบาล|ผู้ป่วย|เกษตรกร|ประชาชน|ผู้บริหาร|บุคลากร|พนักงาน|ลูกค้า|"
             "นักท่องเที่ยว|ผู้บริโภค|ตัวอย่าง")
# A number followed by a duration, an age or a percentage is not a head count.
_NOT_A_COUNT = re.compile(fold_thai(r"\s*(?:years?|yrs?|months?|weeks?|days?|hours?|aged?\b|ปี|เดือน|สัปดาห์|วัน|"
                                    r"ชั่วโมง|%|percent)"))
_AGE_WORD = re.compile(fold_thai(r"\bage[ds]?\b|(?<!สูง)อายุ"))               # ผู้สูงอายุ (the elderly) is no age
# A unit-less figure followed by places or things is not a head count ("a sample of 30 schools").
_NOT_PEOPLE = re.compile(fold_thai(r"\s*(?:schools?|villages?|communit(?:y|ies)|provinces?|districts?|hospitals?|"
                                   r"compan(?:y|ies)|firms?|organi[sz]ations?|enterprises?|smes|institutions?|"
                                   r"universit(?:y|ies)|articles?|papers?|studies|documents?|items?|sites?|"
                                   r"แห่ง|โรงเรียน|หมู่บ้าน|ชุมชน|บริษัท|ชุด|ข้อ)"))
_WHOLE_POPULATION = re.compile(fold_thai(r"ทั้งหมด|ประชากร|population"))
_SAMPLE_PATTERNS: tuple[tuple[re.Pattern, bool], ...] = (     # (pattern, has a unit → no year check)
    (re.compile(fold_thai(r"(?:กลุ่มตัวอย่าง|ผู้ตอบแบบสอบถาม|ผู้ให้ข้อมูลสำคัญ|ผู้ให้ข้อมูล|ผู้เข้าร่วม(?:การ)?วิจัย)")
                + r"(?P<gap>.{0,60}?)" + _NUM + fold_thai(_PERSON_UNITS), re.S), True),
    (re.compile(fold_thai(rf"(?:{_SUBJECTS})") + r"(?P<sgap>[^.;\n]{0,40}?)" + _NUM     # "นักเรียนชั้น ม.3 จำนวน 45 คน"
                + fold_thai(r"\s*(?:คน|ราย|ครัวเรือน)")), True),
    (re.compile(r"\bn\s*=\s*" + _NUM), True),
    (re.compile(_NUM + r"\s+(?:respondents|participants|informants|students|teachers|nurses|patients|farmers|"
                       r"households|employees|subjects|samples|consumers|tourists)\b"), True),
    (re.compile(r"\b(?:sample(?: size)?|respondents|participants)\b(?P<gap>[^0-9.;]{0,30}?)" + _NUM), False),
)
TEXT_COLUMNS = ("title_th", "title_en", "keywords_th", "keywords_en", "abstract_th", "abstract_en")
ARTICLE_COLUMNS = ["article_id", "year", "topic_id", "methods", "sample_size"]


def fold(text: str | None) -> str:
    return fold_thai(clean_text(text)).lower()


def detect_methods(text: str | None) -> list[str]:
    t = fold(text)
    return [k for k, rx in _RX.items() if rx.search(t)]


def sample_size(text: str | None, max_size: int = 1_000_000) -> int | None:
    """A plausible sample size: '...กลุ่มตัวอย่าง ... จำนวน 400 คน', 'นักเรียนจำนวน 400 คน', 'n = 400',
    '400 respondents', 'a sample of 400'. A figure with a person unit (คน / ราย / ครัวเรือน / respondents ...) beats
    a unit-less one wherever it stands; within a tier the first mention wins. A number followed by a duration or an
    age (years, months, ปี, เดือน, aged ...) is skipped, and so is a unit-less number that looks like a year
    (1900–2100, 2400–2600 BE), follows an age word (ผู้สูงอายุ is not one) or counts places or things (schools,
    แห่ง ...). A person-unit figure is checked on the number itself (no age-word test on the text before it). A
    subject count that names the whole population (ทั้งหมด, ประชากร) is not the sample."""
    t = fold(text)
    with_unit, bare = [], []
    for rx, has_unit in _SAMPLE_PATTERNS:
        for m in rx.finditer(t):
            n = int(m.group("num").replace(",", ""))
            if _NOT_A_COUNT.match(t, m.end("num")) or not 2 <= n <= max_size:
                continue
            if not has_unit and (1900 <= n <= 2100 or 2400 <= n <= 2600):
                continue
            if not has_unit and (_AGE_WORD.search(m.group("gap")) or _NOT_PEOPLE.match(t, m.end("num"))):
                continue
            if "sgap" in rx.groupindex and _WHOLE_POPULATION.search(m.group("sgap")):
                continue
            (with_unit if has_unit else bare).append((m.start(), n))
    found = with_unit or bare
    return min(found)[1] if found else None


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
    meta_path = work / "12_methods_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")      # before any LLM call can stop us
    notes, stats = method_notes(cfg, llm)
    if notes is not None:
        write_table(notes, work / "12_methods_notes.parquet")
        meta["llm"] = stats
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    cov = n_with / len(win) if len(win) else 0.0
    print(f"[methods] lexicon {LEXICON_VERSION}: methods named in {cov:.0%} of {len(win):,} articles {start}–{end}; "
          f"{len(topics)} topics summarised ({int(topics['monoculture'].sum()) if len(topics) else 0} monoculture)")
    return am


# ---------------------------------------------------------------------- optional LLM notes (topic level only)
NOTES_PROMPT = "topic_methods.th"
NOTE_COLUMNS = ["topic_id", "th", "en", "source"]
METHOD_NAMES = {m.key: m for m in METHODS}


class MethodsNoteOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    th: str
    en: str

    @field_validator("th", "en")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("empty text")
        return v.strip()


def _top(counts: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(counts.items(), key=lambda kv: (-kv[1], METHOD_KEYS.index(kv[0])))


def method_facts(row, name_th: str, name_en: str, window: tuple[int, int], mono: list[str]) -> str:
    counts = json.loads(row.counts)
    lines = [f"- หัวข้อ: {name_th} / {name_en}",
             f"- บทความช่วง {window[0]}–{window[1]}: {row.articles:,} เรื่อง; ระบุวิธีวิจัยได้ {row.with_methods:,} เรื่อง "
             f"({100 * row.coverage:.0f}%)"]
    for k, n in _top(counts)[:5]:
        m = METHOD_NAMES[k]
        lines.append(f"- {m.th} ({m.en}): {n:,} เรื่อง ({100 * n / row.with_methods:.0f}% ของบทความที่ระบุวิธีได้)")
    if row.ss_n:
        lines.append(f"- ขนาดตัวอย่าง (มัธยฐาน): {row.ss_median:,.0f} จาก {row.ss_n:,} บทความที่ระบุขนาดตัวอย่าง")
    if pd.notna(row.monoculture_share):
        names = " + ".join(METHOD_NAMES[k].th for k in mono)
        lines.append(f"- บทความที่ใช้เฉพาะ {names}: {100 * row.monoculture_share:.0f}% ของบทความที่ระบุวิธีได้")
    return "\n".join(lines)


def template_note(row, name_th: str, name_en: str) -> dict:
    top = _top(json.loads(row.counts))
    if not top:
        return {"th": f"ยังระบุวิธีวิจัยของบทความในหัวข้อ{name_th}ไม่ได้", "en": f"No method could be read for {name_en}."}
    key, n = top[0]
    m, pct = METHOD_NAMES[key], 100 * n / row.with_methods
    return {"th": f"บทความในหัวข้อนี้ที่ระบุวิธีวิจัยได้ {pct:.0f}% ใช้{m.th}",
            "en": f"{pct:.0f}% of the articles in this topic that name a method use {m.en.lower()}."}


def methods_job(cfg: dict) -> LlmJob:
    """LLM job `methods`: one item per topic among the note_top_n largest of work/12_methods_topics."""
    from atlas.export import fine_labels
    from atlas.lineage import topic_code
    from atlas.narrative import grounding_error

    work, mcfg = Path(cfg["pipeline"]["work_dir"]), cfg["methods"]
    topics = read_table(work / "12_methods_topics.parquet")
    labels = fine_labels(read_table(work / "05_labels.parquet")).set_index("topic_id")
    end = int(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["last_complete_year"])
    window = (end - int(mcfg["window_years"]) + 1, end)
    template = load_prompt(NOTES_PROMPT, cfg["llm"]["prompts_dir"])
    sel = topics.sort_values(["articles", "topic_id"], ascending=[False, True]).head(int(mcfg["note_top_n"]))
    am = read_table(work / "12_methods_articles.parquet")
    titles_of = read_table(work / "02_docs.parquet").set_index("article_id")["title"].fillna("").astype(str)
    names = [str(x) for col in ("name_th", "name_en") for x in labels[col].fillna("") if str(x)]
    items = []
    for row in sel.itertuples():
        tid = int(row.topic_id)
        th = str(labels.loc[tid, "name_th"]) if tid in labels.index else topic_code(tid)
        en = str(labels.loc[tid, "name_en"]) if tid in labels.index else topic_code(tid)
        facts = method_facts(row, th, en, window, mcfg["monoculture_methods"])
        in_topic = (am["topic_id"] == tid) & in_window(am["year"], *window)         # the articles the facts describe
        ids = am.loc[in_topic, "article_id"].sort_values().head(int(cfg["narrative"]["n_titles"]))
        titles = "\n".join(f"- {titles_of.get(a, '')}" for a in ids)
        others = [n for n in names if n not in (th, en)]
        items.append(LlmItem(topic_code(tid), render_prompt(template, facts=facts, titles=titles),
                             template_note(row, th, en),
                             lambda out, f=facts + "\n" + titles, o=others: grounding_error([out["th"], out["en"]], f, o)))
    return LlmJob("methods", MethodsNoteOut, prompt_version(template), items)


def _use_llm(cfg: dict, llm) -> bool:
    return llm is not None or (cfg["methods"]["provider"] == "llm" and bool(cfg["llm"]["tasks"]["methods"]["model"]))


def method_notes(cfg: dict, llm=None) -> tuple[pd.DataFrame | None, dict]:
    """(notes, LLM stats) when methods.provider is llm (or an LLM is injected); (None, {}) otherwise."""
    if not _use_llm(cfg, llm):
        if cfg["methods"]["provider"] == "llm":
            print("[methods] methods.provider is llm but llm.tasks.methods.model is empty — no notes this run")
        return None, {}
    job = methods_job(cfg)
    if not job.items:
        return pd.DataFrame(columns=NOTE_COLUMNS), {}
    results, stats = run_job(cfg, job, llm)
    rows = [{"topic_id": int(it.key[1:]), "th": results[it.key].output["th"], "en": results[it.key].output["en"],
             "source": "template" if results[it.key].source == "fallback" else "llm"} for it in job.items]
    return pd.DataFrame(rows, columns=NOTE_COLUMNS), stats
