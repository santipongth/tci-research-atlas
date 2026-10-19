"""Grounded narratives (LLM tasks "narrative" and "brief") — every number comes from the pipeline.

Topic narratives: the top narrative.top_n topics of each status in narrative.statuses (EMERGING, WATCH
and HOT by emerging_score, DECLINING by the steepest share decline) get 2–3 sentences in Thai and
English (prompts/topic_narrative.th.md). Executive brief: a headline and 3–5 bullets for the whole
release (prompts/executive_brief.th.md) — the Overview page's headline sentence.
The prompt carries a facts block built from 05_labels, 07_emerging, 08_forecasts and 06_meta, and the
reply is checked before it is accepted:
  numbers  every number in the text (Thai digits converted, thousands separators removed, sign ignored)
           must equal a number of the facts block — exactly, or rounded to 0 or 1 decimal;
  multiples "N เท่า", "N times", "N-fold", "N×", spelled out (สามเท่า, สิบสองเท่า, ร้อยเท่า, five times,
           hundredfold, tripled, doubled, halved …) must equal a RATIO fact — the "(x เท่า)" values of the
           facts block or the topic's share_ratio, exactly or to 1 decimal — never a window length or a count;
  direction rise/fall words in a rate sentence must agree with the topic's share growth (in the brief: per
           sentence naming one topic, or naming several when the sentence has exactly one rate number);
  names    no topic name may appear unless it is in the facts block.
A failed check → one regeneration that names the problem (llm.max_regenerations); still failing →
a template sentence built from the same facts (source "template"). narrative.provider: template never
calls the LLM. Outputs: work/11_narratives (topic_id, status, th, en, source), work/11_brief.json.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from atlas.io_utils import read_table, write_table
from atlas.label import topic_titles
from atlas.lineage import topic_code
from atlas.llm_runner import LlmItem, LlmJob, run_job
from atlas.prompts import load_prompt, prompt_version, render_prompt
from atlas.state import work_release

TOPIC_PROMPT, BRIEF_PROMPT = "topic_narrative.th", "executive_brief.th"
NARRATIVE_COLUMNS = ["topic_id", "status", "th", "en", "source"]
STATUS_TH = {"EMERGING": "กำลังเกิดใหม่", "WATCH": "จับตา", "HOT": "กำลังร้อน", "DECLINING": "กำลังลดลง",
             "STABLE": "คงที่", "LOW_DATA": "ข้อมูลน้อย"}
_THAI_DIGITS = str.maketrans("".join(chr(0x0E50 + d) for d in range(10)), "0123456789")   # Thai digits 0-9
_NUMBER = re.compile(r"\d+(?:,\d{3}(?!\d))*(?:\.\d+)?")      # "2022,2023" is two numbers, "1,234" one
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
# ---- multiples: numbers, Thai and English number words, verbs ("ratio claims" — checked against ratio facts only)
_TH_DIGIT_WORDS = {"หนึ่ง": 1, "เอ็ด": 1, "สอง": 2, "ยี่": 2, "สาม": 3, "สี่": 4, "ห้า": 5, "หก": 6, "เจ็ด": 7,
                   "แปด": 8, "เก้า": 9}
_TH_UNIT_WORDS = {"สิบ": 10, "ร้อย": 100, "พัน": 1_000, "หมื่น": 10_000, "แสน": 100_000, "ล้าน": 1_000_000}
_TH_WORD = "|".join(sorted([*_TH_DIGIT_WORDS, *_TH_UNIT_WORDS], key=len, reverse=True))
_TH_DIGIT_ALT = "|".join(sorted(_TH_DIGIT_WORDS, key=len, reverse=True))
_TH_MULT = re.compile(rf"((?:{_TH_WORD})+)(?:\s*จุด\s*((?:{_TH_DIGIT_ALT})+))?\s*เท่า")   # สิบสองเท่า, หนึ่งจุดสามเท่า
_EN_SMALL = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                        "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_EN_SMALL.update({w: 10 * i for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split(), 2)})
_EN_SCALE = {"hundred": 100, "thousand": 1_000, "million": 1_000_000}
_EN_WORD = "|".join(sorted([*_EN_SMALL, *_EN_SCALE], key=len, reverse=True))
_EN_MULT = re.compile(rf"\b(?:an?[\s-]+)?((?:{_EN_WORD})(?:[\s-]+(?:and[\s-]+)?(?:{_EN_WORD}))*)[\s-]*(?:times\b|fold\b)",
                      re.I)                                    # five times, twenty-five times, a hundredfold, tenfold
_NUM_MULT = re.compile(r"(\d+(?:\.\d+)?)\s*-?\s*(?:เท่า|times\b|fold\b|×|x\b)", re.I)   # 1.3 เท่า, 3 times, 12-fold, 5x
_NUM_MULT_PRE = re.compile(r"(?:×|\bx)\s*(\d+(?:\.\d+)?)", re.I)                         # ×3
_VERB_MULT = [(re.compile(p, re.I), n) for p, n in (
    (r"\bdoubl(?:e|ed|es|ing)\b(?!-blind)|\btwice\b", 2.0), (r"\btripl(?:e|ed|es|ing)\b|\bthrice\b", 3.0),
    (r"\bquadrupl(?:e|ed|es|ing)\b", 4.0), (r"\bquintupl(?:e|ed|es|ing)\b", 5.0),
    (r"\bhalv(?:e|ed|es|ing)\b|\bby half\b", 0.5))]
_FRACTIONS = [(re.compile(p, re.I), n) for p, n in ((r"\ba half of\b|ครึ่งหนึ่ง", 0.5), ("½", 0.5), ("¼", 0.25),
                                                    ("¾", 0.75))]                       # shares: any number of the facts
_RATIO_FACT = re.compile(r"(\d+(?:\.\d+)?)\s*เท่า")              # "(1.3 เท่า)" in the facts block
_VAGUE_MULT = re.compile(r"เท่าตัว|หลายเท่า|many[- ]?fold|several times|many times", re.I)
_ANY_MULT = re.compile(r"เท่า|\btimes\b|-?fold\b|×|\d\s*x\b|\bx\s*\d", re.I)
# "equals", "equal", "equivalent", "equality", "only", "how much", "as far as", "the same as before": not multiples
_NOT_MULT = re.compile(r"เท่ากับ|เท่ากัน|เทียบเท่า|เท่าเทียม|เท่านั้น|เท่าใด|เท่าไร|เท่าไหร่|เท่าที่|เท่าเดิม")
_RATE_NUMBER = re.compile(r"\d+(?:\.\d+)?\s*(?:%|เปอร์เซ็นต์|percent\b|per\s?cent\b)|ร้อยละ\s*\d+(?:\.\d+)?", re.I)
_RISE = re.compile(r"เพิ่มขึ้น|สูงขึ้น|เติบโต|ขยายตัว|\b(?:grew|grows|growing|increas(?:e|ed|es|ing)|rose|rising)\b", re.I)
_FALL = re.compile(r"ลดลง|หดตัว|ถดถอย|\b(?:declin(?:e|ed|es|ing)|fell|falling|decreas(?:e|ed|es|ing)|dropp(?:ed|ing)|drops?)\b",
                   re.I)
_RATE_CUE = re.compile(r"สัดส่วน|ต่อปี|อัตรา|%|share|per year|a year|annual|/yr", re.I)    # a sentence about the rate
_FLAT = 0.01                                    # |share growth| within ±1% per year: no direction claim is checked


class NarrativeOut(BaseModel):
    th: str
    en: str

    @field_validator("th", "en")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("th and en must not be blank")
        return v.strip()


class BriefOut(BaseModel):
    headline_th: str
    headline_en: str
    bullets_th: list[str] = Field(min_length=1, max_length=6)
    bullets_en: list[str] = Field(min_length=1, max_length=6)

    @field_validator("bullets_th", "bullets_en")
    @classmethod
    def _strip_markers(cls, v: list[str]) -> list[str]:
        """'1. text' / '- text' → 'text' (list numbers are not facts)."""
        return [b for b in (re.sub(r"^\s*(?:\d+[.)]|[-•*])\s+", "", str(x)).strip() for x in v) if b]


# ---------------------------------------------------------------------- grounding check
def numbers_in(text: str) -> list[float]:
    return [float(m.replace(",", "")) for m in _NUMBER.findall(str(text).translate(_THAI_DIGITS))]


def _plain(text: str) -> str:
    """Thai digits → ASCII, thousands separators removed (multiples and rate numbers are read from this)."""
    return _THOUSANDS.sub("", str(text).translate(_THAI_DIGITS))


def _grounded(x: float, allowed: set[float]) -> bool:
    return any(x == a or x == round(a) or x == round(a, 1) for a in allowed)


def _thai_number(words: str, decimals: str | None = None) -> float:
    """สิบสอง → 12, ยี่สิบ → 20, ร้อยเอ็ด → 101, พันห้าร้อย → 1500; หนึ่ง + จุด + สาม → 1.3."""
    total, cur = 0, None
    for w in re.findall(_TH_WORD, words):
        if w in _TH_DIGIT_WORDS:
            cur = _TH_DIGIT_WORDS[w]
        elif w == "ล้าน":
            total, cur = ((total + (cur or 0)) or 1) * 1_000_000, None
        else:
            total, cur = total + (1 if cur is None else cur) * _TH_UNIT_WORDS[w], None
    total += cur or 0
    if decimals:
        return float(f"{total}." + "".join(str(_TH_DIGIT_WORDS[w]) for w in re.findall(_TH_DIGIT_ALT, decimals)))
    return float(total)


def _en_number(words: str) -> float:
    """five → 5, twenty-five → 25, (a) hundred → 100, two hundred and forty → 240."""
    total = cur = 0
    for w in (x for x in re.split(r"[\s-]+", words.lower()) if x and x != "and"):
        if w in _EN_SMALL:
            cur += _EN_SMALL[w]
        elif w == "hundred":
            cur = (cur or 1) * 100
        else:
            total, cur = total + (cur or 1) * _EN_SCALE[w], 0
    return float(total + cur)


def multiples_in(text: str) -> list[float]:
    """Every multiple the text claims, in order: 1.3 เท่า, 3 times, 12-fold, 5x, ×3, สามเท่า, สิบสองเท่า, ร้อยเท่า,
    five times, a hundredfold, doubled/twice (2), tripled (3), quadrupled (4), halved / by half (0.5)."""
    t = _NOT_MULT.sub(" ", _plain(text))
    found = [(m.start(), float(m.group(1))) for pat in (_NUM_MULT, _NUM_MULT_PRE) for m in pat.finditer(t)]
    found += [(m.start(), _thai_number(m.group(1), m.group(2))) for m in _TH_MULT.finditer(t)]
    found += [(m.start(), _en_number(m.group(1))) for m in _EN_MULT.finditer(t)]
    found += [(m.start(), n) for pat, n in _VERB_MULT for m in pat.finditer(t)]
    return [v for _, v in sorted(found)]


def ratio_facts(facts: str) -> list[float]:
    """The ratio values of a facts block — the "(x เท่า)" numbers."""
    return [float(x) for x in _RATIO_FACT.findall(_plain(facts))]


def _ratio_grounded(x: float, ratios) -> bool:
    return any(x == r or x == round(r, 1) or x == round(r, 2) for r in ratios)


def _multiple_error(texts: list[str], ratios: list[float], allowed: set[float], no_baseline: bool,
                    own_terms: list[str] = ()) -> str | None:
    joined = _strip_terms(_NOT_MULT.sub(" ", "\n".join(texts)), list(own_terms))
    if no_baseline and _ANY_MULT.search(joined):
        return "multiple wording for a topic with no baseline (there is nothing to multiply)"
    if _VAGUE_MULT.search(joined):
        return "vague multiple wording (หลายเท่า / เท่าตัว / many-fold): use the numbers in the facts"
    for n in multiples_in(joined):
        if not _ratio_grounded(n, ratios):
            given = (f"the only ratio given is {', '.join(f'{r:g}' for r in ratios)}" if ratios
                     else "the facts give no ratio")
            return (f"multiple {n:g}× is not a ratio in the facts ({given}; a window length or a count is not a "
                    f"multiple) — quote the shares or the ratio as given")
    for pat, n in _FRACTIONS:
        if pat.search(joined) and not _grounded(n, allowed):
            return f"fraction in words ({n:g}) is not in the facts"
    return None


def _strip_terms(text: str, terms: list[str]) -> str:
    """Remove the topic's own names/keywords ("การลดคาร์บอน" is not a claim of decline), longest first."""
    for t in sorted({x.strip() for x in terms if len(x.strip()) >= 2}, key=len, reverse=True):
        text = re.sub(re.escape(t), " ", text, flags=re.I)
    return text


def _direction_error(texts: list[str], growth: float | None, own_terms: list[str] = ()) -> str | None:
    """Direction words are checked only in rate sentences (share / per year / %), after removing own_terms."""
    if growth is None or not math.isfinite(growth) or abs(growth) <= _FLAT:
        return None
    for t in texts:
        for sent in re.split(r"(?<=[.!?])\s+|\n", str(t)):
            if not _RATE_CUE.search(sent):
                continue
            sent = _strip_terms(sent, list(own_terms))
            if growth < 0 and _RISE.search(sent):
                return "direction: the text says the share rises but share growth is negative"
            if growth > 0 and _FALL.search(sent):
                return "direction: the text says the share falls but share growth is positive"
    return None


def _named_direction_error(texts: list[str], named_growth: dict[str, float]) -> str | None:
    """Brief, per sentence: naming one topic → its direction words must match its growth; naming several → checked
    against each of them only when the sentence has exactly one rate number ("A and B grew 12% a year"), else
    skipped ("A grew 12% while B fell 8%" cannot be split reliably — false rejects stay low)."""
    for t in texts:
        for sent in re.split(r"(?<=[.!?])\s+|\n", str(t)):
            low = sent.lower()
            hit = sorted(n for n in named_growth if n.lower() in low)
            if len(hit) >= 2 and len(_RATE_NUMBER.findall(_plain(sent))) != 1:
                continue
            for name in hit:
                err = _direction_error([sent], named_growth[name], hit)
                if err:
                    return f"{err} ({name})"
    return None


def grounding_error(texts: list[str], facts: str, names: list[str], *, no_baseline: bool = False,
                    growth: float | None = None, named_growth: dict[str, float] | None = None,
                    own_terms: list[str] = (), ratios: list[float] | None = None) -> str | None:
    """Why the texts are not grounded in `facts`, or None. names: every topic name of the release.

    no_baseline: the topic has no baseline articles → no multiple wording at all. ratios: the ratio facts a multiple
    may quote (default: the "(x เท่า)" values of `facts`). growth: the topic's share growth (direction words must
    agree, in rate sentences only, after removing own_terms = the topic's names and keywords). named_growth:
    {topic name: growth} for the brief (checked per sentence).
    """
    allowed = set(numbers_in(facts))
    bad = sorted({n for t in texts for n in numbers_in(t) if not _grounded(n, allowed)})
    if bad:
        return "numbers not in the facts: " + ", ".join(f"{n:g}" for n in bad[:5])
    ratios = ratio_facts(facts) if ratios is None else [float(r) for r in ratios if math.isfinite(float(r))]
    err = (_multiple_error(texts, ratios, allowed, no_baseline, own_terms)
           or _direction_error(texts, growth, own_terms))
    if err is None and named_growth:
        err = _named_direction_error(texts, named_growth)
    if err:
        return err
    joined, low_facts = "\n".join(texts).lower(), facts.lower()
    foreign = [n for n in names if len(n) >= 4 and n.lower() not in low_facts and n.lower() in joined]
    if foreign:
        return "names topics that are not in the facts: " + ", ".join(foreign[:3])
    return None


# ---------------------------------------------------------------------- facts
def _pct(v: float, nd: int = 2) -> str:
    return f"{v * 100:.{nd}f}"


def _windows(cfg: dict, last: int) -> tuple[str, str]:
    """('2017–2021 (5 ปี)', '2022–2024 (3 ปี)') — window lengths are facts too ("in the last 3 years")."""
    e = cfg["emerging"]
    r, b = int(e["recent_window"]), int(e["baseline_window"])
    return f"{last - r - b + 1}–{last - r} ({b} ปี)", f"{last - r + 1}–{last} ({r} ปี)"


def topic_facts(cfg: dict, lab, em, fc, last: int) -> str:
    B, R = _windows(cfg, last)
    ci = round(float(cfg["emerging"]["ci_level"]) * 100)
    lines = [f"- ชื่อ: {lab.name_th} ({lab.name_en})",
             f"- สถานะ: {STATUS_TH[em.status]} ({em.status})",
             f"- คำสำคัญ: {lab.keywords}"]
    if str(lab.description).strip():
        lines.append(f"- คำอธิบาย: {lab.description}")
    if float(em.share_baseline) == 0:
        lines.append(f"- ช่วงฐาน {B}: ไม่มีบทความ (หัวข้อใหม่ — ไม่มีฐานเปรียบเทียบ) | ช่วงล่าสุด {R}: "
                     f"{_pct(em.share_recent)}% ของบทความทั้งหมด")
    else:
        lines.append(f"- สัดส่วนของบทความทั้งหมด: ช่วงฐาน {B} = {_pct(em.share_baseline)}% → ช่วงล่าสุด {R} = "
                     f"{_pct(em.share_recent)}% ({em.share_ratio:.1f} เท่า)")
    if pd.notna(em.share_growth):
        lines.append(f"- อัตราเปลี่ยนของสัดส่วนต่อปี: {_pct(em.share_growth, 1)}% (ช่วงเชื่อมั่น {ci}%: "
                     f"{_pct(em.share_growth_lo, 1)}% ถึง {_pct(em.share_growth_hi, 1)}%)")
    lines.append(f"- บทความช่วง {R}: {int(em.count_recent):,} เรื่อง จาก {int(em.n_journals_R)} วารสาร "
                 f"{int(em.n_orgs_R)} สถาบัน")
    if fc is not None and bool(fc.show):
        years, mean, lo, hi = (json.loads(fc[k]) for k in ("fc_years", "fc_mean", "fc_lo80", "fc_hi80"))
        lines.append(f"- พยากรณ์ปี {years[0]}: {mean[0]:.0f} เรื่อง (ช่วง 80%: {lo[0]:.0f}–{hi[0]:.0f})")
    return "\n".join(lines)


def template_narrative(cfg: dict, lab, em, last: int) -> dict:
    B, R = _windows(cfg, last)
    n = int(em.count_recent)
    if float(em.share_baseline) == 0:
        return {"th": f"{lab.name_th}: หัวข้อใหม่ที่ไม่มีบทความในช่วง {B} — ช่วง {R} มี {n:,} เรื่อง "
                      f"({_pct(em.share_recent)}% ของบทความทั้งหมด)",
                "en": f"{lab.name_en}: a new topic with no articles in {B}; {n:,} articles in {R} "
                      f"({_pct(em.share_recent)}% of all articles)."}
    up = float(em.share_recent) >= float(em.share_baseline)
    return {"th": f"{lab.name_th}: สัดส่วนบทความ{'เพิ่มขึ้น' if up else 'ลดลง'}จาก {_pct(em.share_baseline)}% "
                  f"ในช่วง {B} เป็น {_pct(em.share_recent)}% ในช่วง {R} ({n:,} เรื่อง)",
            "en": f"{lab.name_en}: share of articles {'rose' if up else 'fell'} from {_pct(em.share_baseline)}% "
                  f"in {B} to {_pct(em.share_recent)}% in {R} ({n:,} articles)."}


def _inputs(cfg: dict):
    work = Path(cfg["pipeline"]["work_dir"])
    labels = read_table(work / "05_labels.parquet").drop_duplicates("topic_id").set_index("topic_id")
    em = read_table(work / "07_emerging.parquet").set_index("topic_id")
    fpath = work / "08_forecasts.parquet"
    fc = read_table(fpath).set_index("topic_id") if fpath.exists() else pd.DataFrame()
    last = int(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["last_complete_year"])
    return labels, em, fc, last


def selected_topics(cfg: dict, em: pd.DataFrame) -> list[int]:
    ncfg, out = cfg["narrative"], []
    for status in ncfg["statuses"]:
        g = em[em["status"] == status]
        g = g.sort_values("share_growth") if status == "DECLINING" else g.sort_values("emerging_score",
                                                                                         ascending=False)
        out += [int(t) for t in g.index[: int(ncfg["top_n"])]]
    return out


def _names(labels: pd.DataFrame) -> list[str]:
    return [str(n) for c in ("name_th", "name_en") for n in labels[c] if str(n).strip()]


def narrative_job(cfg: dict) -> LlmJob:
    labels, em, fc, last = _inputs(cfg)
    template = load_prompt(TOPIC_PROMPT, cfg["llm"]["prompts_dir"])
    tids = selected_topics(cfg, em)
    titles = topic_titles(cfg, int(cfg["narrative"]["n_titles"])) if tids else {}
    names = _names(labels)
    items = []
    for tid in tids:
        lab, e = labels.loc[tid], em.loc[tid]
        f = fc.loc[tid] if len(fc) and tid in fc.index else None
        facts = topic_facts(cfg, lab, e, f, last)
        tl = "\n".join(f"- {t}" for t in titles.get(tid, []))
        no_base = float(e.share_baseline) == 0
        items.append(LlmItem(topic_code(tid), render_prompt(template, facts=facts, titles=tl),
                             template_narrative(cfg, lab, e, last),
                             _checker(facts + "\n" + tl, names, ("th", "en"),
                                      no_baseline=no_base,
                                      ratios=[] if no_base else [float(e.share_ratio)],    # never a title's "2 เท่า"
                                      growth=float(e.share_growth) if pd.notna(e.share_growth) else None,
                                      own_terms=[str(lab.name_th), str(lab.name_en),
                                                 *str(lab.keywords).split(";")])))
    return LlmJob("narrative", NarrativeOut, prompt_version(template), items)


def _checker(facts: str, names: list[str], fields: tuple[str, ...], **kw):
    def check(out: dict) -> str | None:
        texts = [t for f in fields for t in (out[f] if isinstance(out[f], list) else [out[f]])]
        return grounding_error(texts, facts, names, **kw)
    return check


def brief_facts(cfg: dict, labels: pd.DataFrame, em: pd.DataFrame, last: int) -> str:
    work = Path(cfg["pipeline"]["work_dir"])
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    years = sorted(int(y) for y in meta["totals"])
    counts = em["status"].value_counts()
    ci = round(float(cfg["emerging"]["ci_level"]) * 100)
    analysed, n_all = sum(meta["totals"].values()), int(meta.get("n_articles") or 0)
    lines = [f"- ช่วงข้อมูลที่ใช้วิเคราะห์: {years[0]}–{last}"
             + (f" (ปีที่ยังไม่ครบและไม่นำมาวิเคราะห์: {', '.join(map(str, meta.get('trimmed_years', [])))})"
                if meta.get("trimmed_years") else ""),
             f"- บทความที่นำมาวิเคราะห์ (ปี {years[0]}–{last}): {analysed:,} เรื่อง · หัวข้อวิจัย {len(em)} หัวข้อ"]
    if n_all > analysed:     # the KPI tile counts the whole corpus: give both, each with its label
        lines.append(f"- บทความทั้งคลัง (รวมปีที่ยังไม่ครบและบทความที่ไม่ระบุปี): {n_all:,} เรื่อง")
    lines.append("- จำนวนหัวข้อตามสถานะ: "
                 + ", ".join(f"{STATUS_TH[s]} ({s}) {int(counts.get(s, 0))}" for s in STATUS_TH))
    _, R = _windows(cfg, last)
    for status in ("EMERGING", "HOT", "DECLINING"):
        g = em[em["status"] == status]
        g = g.sort_values("share_growth") if status == "DECLINING" else g.sort_values("emerging_score",
                                                                                         ascending=False)
        for tid, e in g.head(3).iterrows():
            lab = labels.loc[tid]
            line = f"- {STATUS_TH[status]}: {lab.name_th} ({lab.name_en}) — {int(e.count_recent):,} เรื่องใน {R}"
            if pd.notna(e.share_growth):
                line += f", สัดส่วนเปลี่ยน {_pct(e.share_growth, 1)}%/ปี"
                if pd.notna(e.share_growth_lo) and pd.notna(e.share_growth_hi):
                    line += f" (ช่วงเชื่อมั่น {ci}%: {_pct(e.share_growth_lo, 1)}% ถึง {_pct(e.share_growth_hi, 1)}%)"
            lines.append(line)
    return "\n".join(lines)


def template_brief(cfg: dict, em: pd.DataFrame, last: int, total: int, first: int | None = None) -> dict:
    """total = the ANALYSED articles (complete years first–last) — labelled as such, because the Overview's KPI
    tile counts the whole corpus (incl. the running year and undated articles)."""
    c = em["status"].value_counts()
    e, h, d = (int(c.get(s, 0)) for s in ("EMERGING", "HOT", "DECLINING"))
    span = f"{first}–{last}" if first is not None else f"≤ {last}"
    return {"headline_th": f"ข้อมูลปี {span}: วิเคราะห์ {total:,} บทความใน {len(em)} หัวข้อ — กำลังเกิดใหม่ {e} หัวข้อ, "
                           f"กำลังร้อน {h} หัวข้อ, กำลังลดลง {d} หัวข้อ",
            "headline_en": f"Data {span}: {total:,} articles analysed in {len(em)} topics — {e} emerging, {h} hot, "
                           f"{d} declining",
            "bullets_th": [f"{STATUS_TH[s]} ({s}): {int(c.get(s, 0))} หัวข้อ" for s in STATUS_TH],
            "bullets_en": [f"{s}: {int(c.get(s, 0))} topics" for s in STATUS_TH]}


def _named_growth(labels: pd.DataFrame, em: pd.DataFrame) -> dict[str, float]:
    """{topic name (th and en): share growth} for topics with a finite growth - the brief's per-sentence check."""
    out: dict[str, float] = {}
    for tid, g in em["share_growth"].items():
        if tid in labels.index and pd.notna(g):
            for c in ("name_th", "name_en"):
                n = str(labels.loc[tid, c]).strip()
                if len(n) >= 4:
                    out[n] = float(g)
    return out


def brief_job(cfg: dict) -> LlmJob:
    labels, em, _, last = _inputs(cfg)
    work = Path(cfg["pipeline"]["work_dir"])
    totals = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["totals"]
    first = min(int(y) for y in totals) if totals else None
    template = load_prompt(BRIEF_PROMPT, cfg["llm"]["prompts_dir"])
    facts = brief_facts(cfg, labels, em, last)
    item = LlmItem("brief", render_prompt(template, facts=facts),
                   template_brief(cfg, em, last, sum(totals.values()), first),
                   _checker(facts, _names(labels), ("headline_th", "headline_en", "bullets_th", "bullets_en"),
                            named_growth=_named_growth(labels, em), ratios=[]))
    return LlmJob("brief", BriefOut, prompt_version(template), [item])


def _use_llm(cfg: dict, task: str, llm) -> bool:
    return llm is not None or (cfg["narrative"]["provider"] == "llm" and bool(cfg["llm"]["tasks"][task]["model"]))


def narrate(cfg: dict, llm=None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    work_release(cfg)                    # refuse before any LLM call when pipeline.release names another release
    labels, em, _, last = _inputs(cfg)
    stats = {}
    job = narrative_job(cfg)
    if job.items and _use_llm(cfg, "narrative", llm):
        results, stats["narrative"] = run_job(cfg, job, llm)
        outs = {k: (r.output, "template" if r.source == "fallback" else "llm") for k, r in results.items()}
    else:
        outs = {it.key: (it.fallback, "template") for it in job.items}
    rows = []
    for it in job.items:
        tid = int(it.key[1:])
        out, src = outs[it.key]
        rows.append({"topic_id": tid, "status": str(em.loc[tid, "status"]), "th": out["th"], "en": out["en"],
                     "source": src})
    df = pd.DataFrame(rows, columns=NARRATIVE_COLUMNS)
    write_table(df, work / "11_narratives.parquet")
    brief = None
    if cfg["narrative"]["brief"] and len(em):
        bjob = brief_job(cfg)
        if _use_llm(cfg, "brief", llm):
            res, stats["brief"] = run_job(cfg, bjob, llm)
            r = res["brief"]
            brief = {**r.output, "source": "template" if r.source == "fallback" else "llm"}
        else:
            brief = {**bjob.items[0].fallback, "source": "template"}
    (work / "11_brief.json").write_text(json.dumps({"brief": brief, "llm": stats}, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    n_llm = int((df["source"] == "llm").sum())
    print(f"[narrate] {len(df)} topic narratives ({n_llm} LLM, {len(df) - n_llm} template); "
          f"brief: {brief['source'] if brief else 'off'}")
    return df
