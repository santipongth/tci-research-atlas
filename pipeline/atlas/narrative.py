"""Grounded narratives (LLM tasks "narrative" and "brief") — every number comes from the pipeline.

Topic narratives: the top narrative.top_n topics of each status in narrative.statuses (EMERGING, WATCH
and HOT by emerging_score, DECLINING by the steepest share decline) get 2–3 sentences in Thai and
English (prompts/topic_narrative.th.md). Executive brief: a headline and 3–5 bullets for the whole
release (prompts/executive_brief.th.md) — the Overview page's headline sentence.
The prompt carries a facts block built from 05_labels, 07_emerging, 08_forecasts and 06_meta, and the
reply is checked before it is accepted:
  numbers  every number in the text (Thai digits converted, thousands separators removed, sign ignored)
           must equal a number of the facts block — exactly, or rounded to 0 or 1 decimal;
  names    no topic name may appear unless it is in the facts block.
A failed check → one regeneration that names the problem (llm.max_regenerations); still failing →
a template sentence built from the same facts (source "template"). narrative.provider: template never
calls the LLM. Outputs: work/11_narratives (topic_id, status, th, en, source), work/11_brief.json.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from atlas.io_utils import read_table, write_table
from atlas.label import topic_titles
from atlas.lineage import topic_code
from atlas.llm_runner import LlmItem, LlmJob, run_job
from atlas.prompts import load_prompt, prompt_version, render_prompt

TOPIC_PROMPT, BRIEF_PROMPT = "topic_narrative.th", "executive_brief.th"
NARRATIVE_COLUMNS = ["topic_id", "status", "th", "en", "source"]
STATUS_TH = {"EMERGING": "กำลังเกิดใหม่", "WATCH": "จับตา", "HOT": "กำลังร้อน", "DECLINING": "กำลังลดลง",
             "STABLE": "คงที่", "LOW_DATA": "ข้อมูลน้อย"}
_THAI_DIGITS = str.maketrans("".join(chr(0x0E50 + d) for d in range(10)), "0123456789")   # Thai digits 0-9
_NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


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


def _grounded(x: float, allowed: set[float]) -> bool:
    return any(x == a or x == round(a) or x == round(a, 1) for a in allowed)


def grounding_error(texts: list[str], facts: str, names: list[str]) -> str | None:
    """Why the texts are not grounded in `facts`, or None. names: every topic name of the release."""
    allowed = set(numbers_in(facts))
    bad = sorted({n for t in texts for n in numbers_in(t) if not _grounded(n, allowed)})
    if bad:
        return "numbers not in the facts: " + ", ".join(f"{n:g}" for n in bad[:5])
    joined = "\n".join(texts)
    foreign = [n for n in names if len(n) >= 4 and n not in facts and n in joined]
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
        items.append(LlmItem(topic_code(tid), render_prompt(template, facts=facts, titles=tl),
                             template_narrative(cfg, lab, e, last),
                             _checker(facts + "\n" + tl, names, ("th", "en"))))
    return LlmJob("narrative", NarrativeOut, prompt_version(template), items)


def _checker(facts: str, names: list[str], fields: tuple[str, ...]):
    def check(out: dict) -> str | None:
        texts = [t for f in fields for t in (out[f] if isinstance(out[f], list) else [out[f]])]
        return grounding_error(texts, facts, names)
    return check


def brief_facts(cfg: dict, labels: pd.DataFrame, em: pd.DataFrame, last: int) -> str:
    work = Path(cfg["pipeline"]["work_dir"])
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    years = sorted(int(y) for y in meta["totals"])
    counts = em["status"].value_counts()
    ci = round(float(cfg["emerging"]["ci_level"]) * 100)
    lines = [f"- ช่วงข้อมูลที่ใช้วิเคราะห์: {years[0]}–{last}"
             + (f" (ปีที่ยังไม่ครบและไม่นำมาวิเคราะห์: {', '.join(map(str, meta.get('trimmed_years', [])))})"
                if meta.get("trimmed_years") else ""),
             f"- บทความในช่วงนี้: {sum(meta['totals'].values()):,} เรื่อง · หัวข้อวิจัย {len(em)} หัวข้อ",
             "- จำนวนหัวข้อตามสถานะ: " + ", ".join(f"{STATUS_TH[s]} ({s}) {int(counts.get(s, 0))}" for s in STATUS_TH)]
    _, R = _windows(cfg, last)
    for status in ("EMERGING", "HOT", "DECLINING"):
        g = em[em["status"] == status]
        g = g.sort_values("share_growth") if status == "DECLINING" else g.sort_values("emerging_score",
                                                                                         ascending=False)
        for tid, e in g.head(3).iterrows():
            lab = labels.loc[tid]
            lines.append(f"- {STATUS_TH[status]}: {lab.name_th} ({lab.name_en}) — {int(e.count_recent):,} เรื่องใน {R}, "
                         f"สัดส่วนเปลี่ยน {_pct(e.share_growth, 1)}%/ปี (ช่วงเชื่อมั่น {ci}%: "
                         f"{_pct(e.share_growth_lo, 1)}% ถึง {_pct(e.share_growth_hi, 1)}%)")
    return "\n".join(lines)


def template_brief(cfg: dict, em: pd.DataFrame, last: int, total: int) -> dict:
    c = em["status"].value_counts()
    e, h, d = (int(c.get(s, 0)) for s in ("EMERGING", "HOT", "DECLINING"))
    return {"headline_th": f"ข้อมูลถึงปี {last}: {total:,} บทความ {len(em)} หัวข้อ — กำลังเกิดใหม่ {e} หัวข้อ, "
                           f"กำลังร้อน {h} หัวข้อ, กำลังลดลง {d} หัวข้อ",
            "headline_en": f"Data to {last}: {total:,} articles in {len(em)} topics — {e} emerging, {h} hot, "
                           f"{d} declining",
            "bullets_th": [f"{STATUS_TH[s]} ({s}): {int(c.get(s, 0))} หัวข้อ" for s in STATUS_TH],
            "bullets_en": [f"{s}: {int(c.get(s, 0))} topics" for s in STATUS_TH]}


def brief_job(cfg: dict) -> LlmJob:
    labels, em, _, last = _inputs(cfg)
    work = Path(cfg["pipeline"]["work_dir"])
    total = sum(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["totals"].values())
    template = load_prompt(BRIEF_PROMPT, cfg["llm"]["prompts_dir"])
    facts = brief_facts(cfg, labels, em, last)
    item = LlmItem("brief", render_prompt(template, facts=facts), template_brief(cfg, em, last, total),
                   _checker(facts, _names(labels), ("headline_th", "headline_en", "bullets_th", "bullets_en")))
    return LlmJob("brief", BriefOut, prompt_version(template), [item])


def _use_llm(cfg: dict, task: str, llm) -> bool:
    return llm is not None or (cfg["narrative"]["provider"] == "llm" and bool(cfg["llm"]["tasks"][task]["model"]))


def narrate(cfg: dict, llm=None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
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
