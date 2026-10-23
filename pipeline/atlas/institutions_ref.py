"""Canonical institutions (P3): curated alias table → foreign country → ROR dump (CC0, local file) → the
organisation as written.

Resolver.resolve(affiliation_th, affiliation_en, org_key) — the first rule that answers wins:
  1. alias    registry/institutions_aliases.csv (curated; the real file is git-ignored). An alias matches when its
              folded text (atlas.thai.norm_key: case, tone marks, spaces and punctuation ignored) equals the org_key
              or occurs in the folded affiliation — the leftmost, then the longest alias. Rajabhat / Rajamangala
              campuses and abbreviations are rows that map to their university.
  2. foreign  the affiliation names a country other than Thailand (atlas.countries.country_of) → the organisation
              as written, with that country and no province.
  3. ror      a ROR record of the home country whose label, display name or alias (acronyms are too ambiguous)
              equals the organisation part of the affiliation (atlas.orgs.org_name), folded.
  4. name     the organisation as written (P1 org_key), its type from its name, the province named in the
              affiliation (atlas.places) and country TH when the text is Thai or names a Thai province.
Corpus format 1.0 may give hints per affiliation (ror, country, province); they never override an alias:
  a ROR id found in the dump -> that record; a ROR id not in the dump -> key "ror:<id>" (every spelling of the
  organisation is one institution); a country other than TH -> foreign; a province -> used instead of the guess.
Published ids (inst_code) are stable: the alias inst_id, "ror-<id>", or "o" + 10 hex of sha1(org_key).
Institution level only — author names are never read here (PDPA).
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from atlas.countries import country_of
from atlas.openalex import short_id
from atlas.orgs import org_name
from atlas.places import province_finder, provinces
from atlas.thai import clean_text, norm_key, thai_ratio

INST_TYPES = ("university", "rajabhat", "rajamangala", "hospital", "government", "research", "company", "other")
ALIAS_COLUMNS = ("alias", "inst_id", "name_th", "name_en", "type", "province", "country", "ror")
INST_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
ROR_TYPES = {"education": "university", "healthcare": "hospital", "government": "government",
             "facility": "research", "company": "company"}
# (type, folded words) checked in order on the organisation's name — the first hit wins
_TYPE_RULES = tuple((t, tuple(norm_key(w) for w in words)) for t, words in (
    ("rajabhat", ("ราชภัฏ", "rajabhat")),
    ("rajamangala", ("ราชมงคล", "rajamangala")),
    ("hospital", ("โรงพยาบาล", "hospital")),
    ("university", ("มหาวิทยาลัย", "university", "วิทยาลัย", "college", "institute of technology", "สถาบันเทคโนโลยี",
                    "สถาบันบัณฑิต")),
    ("research", ("สถาบันวิจัย", "ศูนย์วิจัย", "research institute", "research center", "research centre")),
    ("company", ("บริษัท", "company", "co ltd", "corporation")),
    ("government", ("กระทรวง", "สำนักงาน", "ministry", "department of", "office of")),
))
_DEPARTMENT = norm_key("กรม")


class AliasError(ValueError):
    """registry/institutions_aliases.csv cannot be used — the message names the row."""


@dataclass(frozen=True)
class Institution:
    key: str
    name_th: str = ""
    name_en: str = ""
    type: str = "other"
    province: str | None = None
    country: str | None = None
    source: str = "name"          # alias | ror | name
    ror: str = ""


def inst_code(key: str) -> str:
    """Published, URL- and file-safe id of an institution key (alias:<id> | ror:<id> | org:<org_key>)."""
    kind, _, rest = key.partition(":")
    if kind == "alias":
        return rest
    if kind == "ror":
        return f"ror-{rest.lower()}"
    return "o" + hashlib.sha1(rest.encode("utf-8")).hexdigest()[:10]


def type_from_name(name: str) -> str:
    folded = norm_key(clean_text(name))
    for t, words in _TYPE_RULES:
        if any(w in folded for w in words):
            return t
    return "government" if folded.startswith(_DEPARTMENT) else "other"   # กรม… (a department), not อุตสาหกรรม


def load_aliases(path: str | Path | None, min_chars: int = 4) -> tuple[dict[str, Institution], dict[str, str]]:
    """({inst_id: Institution}, {folded alias: inst_id}). No path or no file → ({}, {}). Errors name the row."""
    if not path or not Path(path).exists():
        return {}, {}
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = [str(c).strip() for c in (reader.fieldnames or [])]
        unknown = sorted(set(cols) - set(ALIAS_COLUMNS))
        if unknown or not {"alias", "inst_id"} <= set(cols):
            raise AliasError(f"{path}: columns must come from {list(ALIAS_COLUMNS)} and include alias and inst_id "
                             f"(unknown columns: {unknown})")
        rows = [{str(k).strip(): (v or "").strip() for k, v in r.items() if k} for r in reader]
    known = provinces()
    attrs: dict[str, dict[str, str]] = {}
    first: dict[str, str] = {}
    aliases: dict[str, str] = {}
    for n, r in enumerate(rows, start=2):
        where, iid, alias = f"{path} row {n}", r.get("inst_id", ""), r.get("alias", "")
        if not INST_ID.fullmatch(iid) or iid.startswith("ror-"):
            raise AliasError(f"{where}: inst_id {iid!r} must be 2–41 lower-case letters, digits or '-' (not ror-…)")
        folded = norm_key(clean_text(alias))
        if len(folded) < min_chars:
            raise AliasError(f"{where}: alias {alias!r} is shorter than institutions.alias_min_chars ({min_chars}) "
                             "once folded — too ambiguous")
        if aliases.get(folded, iid) != iid:
            raise AliasError(f"{where}: alias {alias!r} already maps to {aliases[folded]!r}")
        aliases[folded] = iid
        first.setdefault(iid, alias)
        given = {"name_th": r.get("name_th", ""), "name_en": r.get("name_en", ""), "type": r.get("type", ""),
                 "province": r.get("province", "").upper(), "country": r.get("country", "").upper(),
                 "ror": short_id(r.get("ror", "")).lower()}
        if given["type"] and given["type"] not in INST_TYPES:
            raise AliasError(f"{where}: type {given['type']!r} is not one of {list(INST_TYPES)}")
        if given["province"] and given["province"] not in known:
            raise AliasError(f"{where}: province {given['province']!r} is not an ISO 3166-2:TH code such as TH-10")
        if given["country"] and not re.fullmatch(r"[A-Z]{2}", given["country"]):
            raise AliasError(f"{where}: country {given['country']!r} is not a two-letter ISO code")
        a = attrs.setdefault(iid, {})
        for k, v in given.items():
            if v and a.get(k, v) != v:
                raise AliasError(f"{where}: {k} {v!r} contradicts {a[k]!r} given for {iid} on an earlier row")
            if v:
                a[k] = v
    insts = {}
    for iid, a in attrs.items():
        th = a.get("name_th") or (first[iid] if thai_ratio(first[iid]) > 0.5 else "")
        en = a.get("name_en") or ("" if th else first[iid])
        insts[iid] = Institution(key=f"alias:{iid}", name_th=th, name_en=en,
                                 type=a.get("type") or type_from_name(f"{th} {en}"), province=a.get("province"),
                                 country=a.get("country") or "TH", source="alias", ror=a.get("ror", ""))
    return insts, aliases


def _read_dump(p: Path) -> list:
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".json")]
            if not names:
                raise ValueError(f"{p}: no .json file inside the zip")
            pick = next((n for n in names if n.lower().endswith("schema_v2.json")), names[0])
            with z.open(pick) as f:
                return json.load(f)
    return json.loads(p.read_text(encoding="utf-8"))


def _ror_province(d: dict) -> str | None:
    code = str(d.get("country_subdivision_code") or "").upper()
    if code in provinces():                 # ISO "TH-65"; bare GeoNames admin codes are not ISO → read the names
        return code
    return province_finder().find("", f"{d.get('country_subdivision_name') or ''}, {d.get('name') or ''}")


def ror_record(x: dict, country: str) -> dict | None:
    """The fields the resolver uses from one ROR v2 record located in `country` (None: elsewhere or inactive)."""
    details = [loc.get("geonames_details") or {} for loc in x.get("locations") or []]
    here = next((d for d in details if d.get("country_code") == country), None)
    if here is None or x.get("status", "active") != "active":
        return None
    names = x.get("names") or []
    usable = [n["value"] for n in names
              if n.get("value") and set(n.get("types") or []) & {"ror_display", "label", "alias"}]
    th = next((n["value"] for n in names if n.get("lang") == "th" and n.get("value")), "")
    en = next((n["value"] for n in names if "ror_display" in (n.get("types") or [])), usable[0] if usable else "")
    base = next((ROR_TYPES[t] for t in x.get("types") or [] if t in ROR_TYPES), "other")
    refined = type_from_name(f"{th} {en}")
    return {"id": short_id(x.get("id")).lower(), "names": usable, "name_th": th, "name_en": en,
            "type": refined if refined in ("rajabhat", "rajamangala") else base, "province": _ror_province(here)}


def load_ror(path: str | Path | None, country: str, cache_dir: str | Path) -> list[dict]:
    """ROR records located in `country`. The dump (downloaded by the maintainer) is read once; the subset is cached
    as cache_dir/<dump name>.<country>.json and reused while it is newer than the dump. Never touches the network."""
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        print(f"[institutions] WARNING: institutions.ror_path {p} does not exist — ROR matching skipped")
        return []
    cache = Path(cache_dir) / f"{p.stem}.{country}.json"
    if cache.exists() and cache.stat().st_mtime >= p.stat().st_mtime:
        return json.loads(cache.read_text(encoding="utf-8"))
    out = [r for r in (ror_record(x, country) for x in _read_dump(p)) if r]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"[institutions] ROR: {len(out):,} records in {country} from {p.name}")
    return out


class Resolver:
    """Affiliation → Institution (None when the author row names no organisation at all)."""

    def __init__(self, aliases: tuple[dict[str, Institution], dict[str, str]], ror: list[dict],
                 find_province: bool = True):
        self.insts, self.alias_to_id = aliases
        self._alias_rx = (re.compile("|".join(re.escape(a) for a in sorted(self.alias_to_id, key=len, reverse=True)))
                          if self.alias_to_id else None)
        self.ror: dict[str, dict] = {}
        self.ror_by_id: dict[str, dict] = {}
        for r in ror:
            self.ror_by_id.setdefault(str(r["id"]).lower(), r)
            for name in r["names"]:
                self.ror.setdefault(norm_key(name), r)
        self.find_province = find_province

    def _alias(self, th: str, en: str, key: str) -> Institution | None:
        iid = self.alias_to_id.get(key)
        if iid is None and self._alias_rx is not None:
            m = self._alias_rx.search(norm_key(f"{th} {en}"))
            iid = self.alias_to_id[m.group(0)] if m else None
        return self.insts[iid] if iid is not None else None

    @staticmethod
    def _ror_inst(r: dict) -> Institution:
        return Institution(key=f"ror:{r['id']}", name_th=r["name_th"], name_en=r["name_en"], type=r["type"],
                           province=r["province"], country="TH", source="ror", ror=r["id"])

    def resolve(self, affiliation_th: str | None, affiliation_en: str | None, org_key: str | None,
                ror: str | None = None, country: str | None = None, province: str | None = None) -> Institution | None:
        th, en, key = clean_text(affiliation_th), clean_text(affiliation_en), str(org_key or "")
        if not (th or en or key):
            return None
        found = self._alias(th, en, key)
        if found is not None:
            return found
        if not key:
            return None
        name = org_name(th, en)
        names = {"name_th": name, "name_en": ""} if thai_ratio(name) > 0.5 else {"name_th": "", "name_en": name}
        country = (country or "").upper() or country_of(th, en)
        province = province or None
        rid = short_id(ror).lower() if ror else ""
        if rid and rid in self.ror_by_id:
            return self._ror_inst(self.ror_by_id[rid])
        if country and country != "TH":
            return Institution(key=f"ror:{rid}" if rid else f"org:{key}", type=type_from_name(name), country=country,
                               ror=rid, **names)
        if rid:
            if province is None and self.find_province:
                province = province_finder().find(th, en)
            return Institution(key=f"ror:{rid}", type=type_from_name(name), ror=rid, country="TH", province=province,
                               **names)
        for cand in (org_name(th, ""), org_name("", en)):
            r = self.ror.get(norm_key(cand)) if cand else None
            if r is not None:
                return self._ror_inst(r)
        if province is None and self.find_province:
            province = province_finder().find(th, en)
        thai = country == "TH" or thai_ratio(th) > 0 or province is not None
        return Institution(key=f"org:{key}", type=type_from_name(name), province=province,
                           country="TH" if thai else None, **names)
