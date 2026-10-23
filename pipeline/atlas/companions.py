"""The files that travel with a corpus (format 1.0) and `atlas profile` checks for the data team:

  journals.csv              one row per journal_key (names, ISSN, TCI tier and field) — required for corpus_jsonl
  institutions_aliases.csv  written affiliation → one institution (registry/institutions_aliases.example.csv)
  province_population.csv   code,population,year → articles per 100,000 people
  ror.zip                   a ROR data dump (CC0) for matching institutions

Each file is read with the loader the pipeline itself uses, so an error here is the error the run would hit.
For the alias table the check also lists the most frequent affiliations no alias covers yet (a to-do CSV with the
alias columns to fill in) — institution level only, never a person.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from atlas.institutions import load_population
from atlas.institutions_ref import ALIAS_COLUMNS, AliasError, Resolver, load_aliases
from atlas.orgs import org_display_names
from atlas.places import provinces
from atlas.registry import RegistryError, journal_keys, load_registry

FILES = {"journals": "journals.csv", "aliases": "institutions_aliases.csv",
         "population": "province_population.csv", "ror": "ror.zip"}


def companion_paths(root: str | Path) -> dict[str, Path]:
    """The companion files present in the corpus folder."""
    root = Path(root)
    return {k: root / f for k, f in FILES.items() if root.is_dir() and (root / f).is_file()}


def _journals(path: Path | None, arts: pd.DataFrame) -> dict:
    used = set(journal_keys(arts)) - {""} if len(arts) else set()
    if path is None:
        return {"present": False, "journals_in_articles": len(used)}
    try:
        df, warnings = load_registry(path)
    except RegistryError as e:
        return {"present": True, "error": str(e)}
    missing = sorted(used - set(df["journal_key"]))
    unused = sorted(set(df["journal_key"]) - used)
    blank = {c: int((df[c].fillna("").astype(str) == "").sum()) for c in ("name_th", "name_en", "tci_field")}
    return {"present": True, "rows": len(df), "warnings": warnings[:20], "n_warnings": len(warnings),
            "missing_keys": missing[:50], "n_missing": len(missing), "unused_keys": unused[:20], "n_unused": len(unused),
            "no_tier": int(df["tci_tier"].isna().sum()), "blank": blank}


def _aliases(path: Path | None, auths: pd.DataFrame, todo: Path | None, top: int) -> dict:
    try:
        table = load_aliases(path)
    except AliasError as e:
        return {"present": path is not None, "error": str(e)}
    res = Resolver(table, [], find_province=False)
    a = auths[["article_id", "affiliation_th", "affiliation_en", "org_key"]].copy() if len(auths) else pd.DataFrame(
        columns=["article_id", "affiliation_th", "affiliation_en", "org_key"])
    for c in ("affiliation_th", "affiliation_en", "org_key"):
        a[c] = a[c].fillna("").astype(str)
    a = a[(a["affiliation_th"] != "") | (a["affiliation_en"] != "")]
    trip = a[["affiliation_th", "affiliation_en", "org_key"]].drop_duplicates()
    hit = [getattr(res.resolve(t, e, k), "source", "") == "alias" for t, e, k in trip.itertuples(index=False)]
    a = a.merge(trip.assign(alias_hit=hit), on=["affiliation_th", "affiliation_en", "org_key"], how="left")
    rows = len(a)
    covered = int(a["alias_hit"].sum()) if rows else 0
    names = org_display_names(auths) if len(auths) else {}
    miss = a[~a["alias_hit"].astype(bool) & (a["org_key"] != "")]
    counts = miss.groupby("org_key")["article_id"].nunique().sort_values(ascending=False, kind="stable")
    todo_rows = [{"alias": names.get(k, k), "articles": int(n)} for k, n in counts.head(top).items()]
    if todo is not None:
        todo.parent.mkdir(parents=True, exist_ok=True)
        with todo.open("w", encoding="utf-8-sig", newline="") as f:      # BOM: opens cleanly in Excel
            w = csv.DictWriter(f, fieldnames=[*ALIAS_COLUMNS, "articles"])
            w.writeheader()
            w.writerows({**dict.fromkeys(ALIAS_COLUMNS, ""), **r} for r in todo_rows)
    return {"present": path is not None, "institutions": len(table[0]), "aliases": len(table[1]),
            "affiliation_rows": rows, "covered_pct": round(100 * covered / rows, 1) if rows else 0.0,
            "top_uncovered": todo_rows[:30], "todo_csv": str(todo) if todo is not None else None}


def _population(path: Path | None) -> dict:
    if path is None:
        return {"present": False}
    try:
        pop = load_population(path)
    except (ValueError, KeyError) as e:
        return {"present": True, "error": str(e)}
    have = set((pop or {}).get("by_code", {}))
    return {"present": True, "provinces": len(have), "missing": sorted(set(provinces()) - have),
            "year": (pop or {}).get("year")}


def check_companions(root: str | Path, arts: pd.DataFrame, auths: pd.DataFrame, todo: Path | None = None,
                     top: int = 300, required: bool = True) -> dict:
    """Report on every companion file; `problems` lists what must be fixed before the hand-over."""
    p = companion_paths(root)
    out = {"journals": _journals(p.get("journals"), arts), "aliases": _aliases(p.get("aliases"), auths, todo, top),
           "population": _population(p.get("population")),
           "ror": {"present": "ror" in p, "bytes": p["ror"].stat().st_size if "ror" in p else 0}}
    problems = [f"{k}: {v['error']}" for k, v in out.items() if v.get("error")]
    j = out["journals"]
    if required and not j["present"]:
        problems.append("journals.csv is missing from the corpus folder")
    if j.get("n_missing"):
        problems.append(f"journals.csv has no row for {j['n_missing']} journal_key(s) used by the articles, "
                        f"e.g. {', '.join(j['missing_keys'][:5])}")
    pop = out["population"]
    if pop.get("present") and not pop.get("error") and pop["missing"]:
        problems.append(f"province_population.csv lacks {len(pop['missing'])} province(s), e.g. "
                        f"{', '.join(pop['missing'][:5])}")
    out["problems"] = problems
    return out


def render(c: dict) -> list[str]:
    """Markdown lines for the profile report."""
    j, a, pop = c["journals"], c["aliases"], c["population"]
    lines = ["## Companion files (journals · institutions · provinces · ROR)", ""]
    if c["problems"]:
        lines += ["**ต้องแก้ก่อนส่ง:**", "", *(f"- \N{WARNING SIGN} {x}" for x in c["problems"]), ""]
    else:
        lines += ["- ไม่มีปัญหาที่ต้องแก้", ""]
    if j.get("present") and not j.get("error"):
        lines.append(f"- journals.csv: {j['rows']:,} วารสาร · ไม่มี tci_tier {j['no_tier']:,} · "
                     f"ไม่มี tci_field {j['blank']['tci_field']:,} · ไม่มีชื่อไทย {j['blank']['name_th']:,} · "
                     f"ไม่มีบทความในคลัง {j['n_unused']:,} · คำเตือน {j['n_warnings']:,}")
        lines += [f"  - {w}" for w in j["warnings"][:10]]
    if not a.get("error"):
        lines.append(f"- institutions_aliases.csv: {'มี' if a['present'] else 'ยังไม่มี'} · สถาบัน {a['institutions']:,} · "
                     f"ชื่อเรียก {a['aliases']:,} · ครอบคลุมแถวสังกัด {a['covered_pct']}%"
                     + (f" · รายการที่ยังไม่ครอบคลุม → `{a['todo_csv']}`" if a.get("todo_csv") else ""))
        if a["top_uncovered"]:
            lines += ["", "| สังกัดที่พบบ่อยแต่ยังไม่มีใน institutions_aliases.csv | บทความ |", "|---|---|",
                      *(f"| {r['alias']} | {r['articles']:,} |" for r in a["top_uncovered"][:20])]
    if pop.get("present") and not pop.get("error"):
        lines.append(f"- province_population.csv: {pop['provinces']} จังหวัด · ปี {pop['year']}")
    lines += [f"- ror.zip: {'มี' if c['ror']['present'] else 'ไม่มี (ไม่บังคับ)'}", ""]
    return lines
