"""Parser for ThaiJO-scraped Markdown articles (one .md file per article).

Pure functions, stdlib + atlas.thai only. `parse_markdown` never raises on malformed
input: missing sections simply yield empty values.
"""
from __future__ import annotations

import re
from statistics import median

from atlas.thai import (
    LATIN_LETTER,
    MARKS,
    THAI_LETTER,
    clean_text,
    fold_thai,
    has_pua,
    norm_key,
    repair_glyphs,
    thai_ratio,
)

MAI_THO = "\N{THAI CHARACTER MAI THO}"
BOM = "\N{ZERO WIDTH NO-BREAK SPACE}"

_FIELD = re.compile(r"^\*\*(?P<key>[A-Za-z ]+):\*\*\s*(?P<val>.*)$")
_URL_ID = re.compile(r"https?://(?P<host>[^./]+)\.[^/]+/index\.php/(?P<journal>[^/]+)/article/view/(?P<id>\d+)")
_DOI = re.compile(r"DOI:\s*(?:https?://(?:dx\.)?doi\.org/)?(?P<doi>10\.\d{4,9}/\S+)", re.I)
_DOI_YEAR = re.compile(r"\.((?:19|20)\d{2})\.\d+$")
_PAREN_YEAR = re.compile(r"\([^()]*?\b((?:19|20|25)\d{2})[a-z]?\b[^()]*?\)")
_LATIN_AUTHOR_START = re.compile(r"^[A-Z][A-Za-z'\-]+,\s+(?:[A-Z]\.|[A-Z][a-z]+)")
_LONE_INITIAL = re.compile(r"^[A-Z]\.\s*\(")
_SEG_SPLIT = re.compile(r"\s{2,}")
_ABSTRACT_LABEL = re.compile(r"^(abstract|บทคัดย่อ)[:.]?$", re.I)
_STAT_SYMBOL_LOSS = re.compile(r"\(\s*=\s*\d")

STUDENT_ROLES = ["นักศึกษาปริญญาเอก", "นักศึกษาปริญญาโท", "นิสิตปริญญาเอก", "นิสิตปริญญาโท",
                 "นักศึกษา", "นิสิต", "Graduate student", "Ph.D. student", "PhD student",
                 "Doctoral student", "Master's student", "Student"]
ACADEMIC_ROLES = ["รองศาสตราจารย์", "ผู้ช่วยศาสตราจารย์", "ศาสตราจารย์", "อาจารย์",
                  "Associate Professor", "Assistant Professor", "Professor", "Lecturer"]


# ------------------------------------------------------------------ sections
def _split_sections(text: str) -> tuple[str, dict, dict[str, str]]:
    """→ (h1 title, header fields, {lower-case section name: body})."""
    lines = text.replace("\r\n", "\n").lstrip(BOM).split("\n")
    title = ""
    fields: dict = {}
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    key: str | None = None
    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            if current:
                sections[current] = "\n".join(buf).strip()
            current, buf = line[3:].strip().lower(), []
            continue
        if current:
            buf.append(line)
            continue
        m = _FIELD.match(line.strip())
        if m:
            key = m.group("key").strip().lower()
            fields[key] = m.group("val").strip()
        elif line.strip().startswith("- ") and key == "authors":
            fields.setdefault("authors_list", []).append(line.strip()[2:].strip())
    if current:
        sections[current] = "\n".join(buf).strip()
    return title, fields, sections


# ------------------------------------------------------------------ title
def split_title(h1: str) -> tuple[str, str]:
    """'TH [EN]' or 'EN (TH)' or single-language → (title_th, title_en)."""
    h1 = clean_text(h1)
    m = re.match(r"^(?P<main>.+?)\s*[\[(](?P<alt>[^\[\]()]+)[\])]\s*$", h1)
    if m:
        main, alt = m.group("main").strip(), m.group("alt").strip()
        main_th, alt_th = thai_ratio(main) > 0.5, thai_ratio(alt) > 0.5
        substantial = len(THAI_LETTER.findall(alt)) + len(LATIN_LETTER.findall(alt)) >= 15
        if main_th != alt_th and substantial:
            return (main, alt) if main_th else (alt, main)
    return (h1, "") if thai_ratio(h1) > 0.5 else ("", h1)


# ------------------------------------------------------------------ abstract
def split_abstract(raw: str, need_en_title: bool) -> dict:
    """ThaiJO joins TH abstract, EN title, EN abstract and DOI with runs of >=2 spaces."""
    raw = repair_glyphs(raw).replace("\n", " ")
    doi = ""
    m = _DOI.search(raw)
    if m:
        doi = m.group("doi").rstrip(".,;)")
        raw = raw[: m.start()]
    segs = [s.strip() for s in _SEG_SPLIT.split(raw) if s.strip()]
    segs = [s for s in segs if not _ABSTRACT_LABEL.match(s)]
    th_parts: list[str] = []
    en_segs: list[str] = []
    for s in segs:
        (th_parts if thai_ratio(s) > 0.5 else en_segs).append(s)
    en_title = ""
    if need_en_title and len(en_segs) >= 2:
        first = en_segs[0]
        if len(first) <= 250 and not first.endswith("."):
            title_parts, i = [first], 1
            # a title broken by a space run continues with a lower-case fragment
            while (i < len(en_segs) - 1 and en_segs[i][:1].islower()
                   and len(en_segs[i]) <= 120 and not en_segs[i].endswith(".")):
                title_parts.append(en_segs[i])
                i += 1
            en_title, en_segs = " ".join(title_parts), en_segs[i:]
    return {
        "abstract_th": clean_text(" ".join(th_parts)),
        "abstract_en": clean_text(" ".join(en_segs)),
        "title_en_from_abstract": clean_text(en_title),
        "doi": doi,
    }


# ------------------------------------------------------------------ keywords
def split_keywords(raw: str) -> tuple[list[str], list[str]]:
    th: list[str] = []
    en: list[str] = []
    for k in re.split(r"[,;]", clean_text(raw)):
        k = k.strip()
        if k:
            (th if thai_ratio(k) > 0.5 else en).append(k)
    return th, en


# ------------------------------------------------------------------ authors
def _role_regex(word: str) -> re.Pattern:
    # tolerate missing/extra Thai marks between letters (marks are often lost in extraction)
    parts = [re.escape(ch) + f"[{MARKS}]*" for ch in fold_thai(word)]
    return re.compile(r"^\s*" + "".join(parts) + r"\s*(?:ประจำ)?\s*", re.I)


_ROLE_PATTERNS = [(w, _role_regex(w), w in STUDENT_ROLES) for w in STUDENT_ROLES + ACADEMIC_ROLES]


def _strip_role(s: str) -> tuple[str, str, bool]:
    for word, rx, is_student in _ROLE_PATTERNS:
        m = rx.match(s)
        if m:
            return s[m.end():].strip().lstrip(",;:- ").strip(), word, is_student
    return s.strip(), "", False


def _outer_paren(s: str) -> tuple[str, str]:
    """'name ... (affiliation (nested))' → (prefix, content of the trailing top-level group)."""
    depth, start = 0, 0
    for i, ch in enumerate(s):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
            if depth == 0 and s[i + 1:].strip() == "":
                return s[:start].strip(), s[start + 1:i].strip()
    return s.strip(), ""


def parse_author(line: str) -> dict:
    line = clean_text(line)
    head, aff = _outer_paren(line)
    name, name_en = head, ""
    m = re.match(r"^(?P<name>[^\[]+?)\s*\[(?P<en>[^\]]+)\]\s*$", head)
    if m:
        name, name_en = m.group("name").strip(), m.group("en").strip()
    aff_th, aff_en = aff, ""
    inner = re.match(r"^(?P<th>.*?)\s*\((?P<en>.*)\)\s*$", aff)
    if inner and thai_ratio(inner.group("th")) > 0.5 and thai_ratio(inner.group("en")) <= 0.5:
        aff_th, aff_en = inner.group("th"), inner.group("en")
    elif aff and thai_ratio(aff) <= 0.5:
        aff_th, aff_en = "", aff
    aff_th, role, is_student = _strip_role(aff_th)
    aff_en, role_en, student_en = _strip_role(aff_en)
    return {"name": name, "name_en": name_en,
            "affiliation_th": aff_th, "affiliation_en": aff_en,
            "role": role or role_en, "is_student": is_student or student_en}


# ------------------------------------------------------------------ references
def rejoin_references(lines: list[str]) -> list[dict]:
    """ThaiJO wraps long references onto new bullets — stitch them back together."""
    refs: list[dict] = []
    translated = False
    for raw in lines:
        line = clean_text(raw.strip().lstrip("-").strip())
        if not line:
            continue
        if re.fullmatch(r"translated (thai )?references", line, re.I):
            translated = True
            continue
        cur = refs[-1] if refs else None
        has_year = bool(_PAREN_YEAR.search(line[:150]))
        starts_new = (
            cur is None
            or (has_year and cur["year"] is not None and not _LONE_INITIAL.match(line))
            or (bool(_LATIN_AUTHOR_START.match(line)) and cur["year"] is not None
                and cur["text"].endswith("."))
        )
        if starts_new or cur is None:
            refs.append({"text": line, "year": None, "translated": translated})
        else:
            cur["text"] = f"{cur['text']} {line}"
        last = refs[-1]
        if last["year"] is None:
            last["year"] = reference_year(last["text"])
    for r in refs:
        r["lang"] = reference_lang(r["text"])
    return refs


def reference_year(text: str) -> int | None:
    """The first parenthesised year of a reference, Common Era (Buddhist Era years are converted)."""
    y = _PAREN_YEAR.search(text)
    if not y:
        return None
    year = int(y.group(1))
    return year - 543 if year > 2400 else year


def reference_lang(text: str) -> str:
    return "th" if thai_ratio(text) > 0.3 else "latin"


def mark_self_citations(refs: list[dict], title_th: str, title_en: str) -> list[dict]:
    """Set r["self_citation"] (the reference quotes the article's own title) → the references that count:
    neither self-citations nor the romanised copies of Thai references."""
    keys = [norm_key(t)[:40] for t in (title_th, title_en) if len(norm_key(t)) >= 12]
    for r in refs:
        r["self_citation"] = any(k in norm_key(r["text"]) for k in keys)
    return [r for r in refs if not r["self_citation"] and not r["translated"]]


def quality_flags(raw: str, abstract_th: str, abstract_en: str) -> list[str]:
    """text_quality flags: PUA glyphs in the raw text, Thai abstract without tone marks, lost statistics symbols."""
    flags = ["thai_pua_repaired"] if has_pua(raw) else []
    th_letters = len(THAI_LETTER.findall(abstract_th))
    if th_letters >= 200 and abstract_th.count(MAI_THO) / th_letters < 0.005:
        flags.append("tone_marks_missing")
    if _STAT_SYMBOL_LOSS.search(abstract_th + " " + abstract_en):
        flags.append("stat_symbols_missing")
    return flags


# ------------------------------------------------------------------ year
def resolve_year(published: str, doi: str) -> tuple[int | None, str]:
    m = re.match(r"^(\d{4})", published or "")
    if m and int(m.group(1)) != 1970:          # 1970-01-01 = date lost in the scrape
        y = int(m.group(1))
        return (y - 543 if y > 2400 else y), "published"
    m = _DOI_YEAR.search(doi or "")
    if m:
        return int(m.group(1)), "doi"
    return None, ""


def fill_years_from_issue(records: list[dict]) -> None:
    """Corpus-level pass: articles still missing a year take the median year of their issue."""
    by_issue: dict[str, list[int]] = {}
    for r in records:
        if r["year"] is not None and r["issue_url"]:
            by_issue.setdefault(r["issue_url"], []).append(r["year"])
    for r in records:
        if r["year"] is None and by_issue.get(r["issue_url"]):
            r["year"] = int(median(by_issue[r["issue_url"]]))
            r["year_source"] = "issue_median"


# ------------------------------------------------------------------ main
def parse_markdown(text: str, source_path: str = "") -> dict:
    h1, f, sec = _split_sections(text)
    title_th, title_en = split_title(h1)
    ab = split_abstract(sec.get("abstract", ""), need_en_title=not title_en)
    title_en = title_en or ab["title_en_from_abstract"]
    kw_th, kw_en = split_keywords(f.get("keywords", ""))
    authors = [parse_author(a) for a in f.get("authors_list", [])]

    url = f.get("article url", "")
    article_id, journal = "", f.get("journal", "")
    um = _URL_ID.search(url)
    if um:
        article_id = f"{um.group('host')}:{um.group('journal')}:{um.group('id')}"
        journal = journal or um.group("journal")
    year, year_source = resolve_year(f.get("published", ""), ab["doi"])

    ref_lines = [ln for ln in sec.get("references", "").split("\n") if ln.strip()]
    refs = rejoin_references(ref_lines)
    counted = mark_self_citations(refs, title_th, title_en)
    flags = quality_flags(text, ab["abstract_th"], ab["abstract_en"])

    return {
        "article_id": article_id,
        "source_path": source_path,
        "url": url,
        "issue_url": f.get("issue url", ""),
        "journal_name": journal,
        "published": f.get("published", ""),
        "year": year,
        "year_source": year_source,
        "pages": f.get("pages", ""),
        "title_th": title_th,
        "title_en": title_en,
        "abstract_th": ab["abstract_th"],
        "abstract_en": ab["abstract_en"],
        "doi": ab["doi"],
        "keywords_th": kw_th,
        "keywords_en": kw_en,
        "authors": authors,
        "references": refs,
        "n_references": len(counted),
        "has_references": bool(refs),
        "self_citation_only": bool(refs) and not counted and any(r["self_citation"] for r in refs),
        "text_quality": flags,
    }
