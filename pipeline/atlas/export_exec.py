"""Contract 2.2 files of the executives' release (P3), built from work/15_* (institutions), 16_* (SDG), 17_*
(benchmark) and 18_* (gaps). Called by atlas.export_v2.build_release; each module is optional — a missing checkpoint
leaves its file (and its manifest.modules entry) out; a module skipped for a reason is named in
manifest.skipped_modules.

institutions.json          published institutions (≥ institutions.min_articles in the window), KPI shares, the
                           partnership network (top pairs), partner countries, names of the provinces used
institutions/<id>.json     years, topics, partners, partner countries, R6 suggestions
regions.json               articles per province and region (+ per 100,000 people when the population table is given)
sdg.json                   the goals of every framework with their topics and recent output
global.json                Thailand vs the world per OpenAlex subfield (E9)
gaps.json                  R5 gap lists and E10 concentration
overview.executive         template sentences from the files above (no LLM; every number from the files)
Only institution-level aggregates are published; no person, no abstract.
"""
from __future__ import annotations

import json
import math
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from atlas.countries import COUNTRY_NAMES
from atlas.institutions_ref import INST_TYPES
from atlas.io_utils import read_table
from atlas.places import REGIONS, provinces
from atlas.registry import journal_path
from atlas.schema import contract as C


def _f(v, nd: int = 4) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if math.isfinite(x) else None


def _opt(path: Path) -> pd.DataFrame | None:
    try:
        return read_table(path)
    except FileNotFoundError:
        return None


def _meta(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _window(pair) -> C.YearWindow:
    return C.YearWindow(start=int(pair[0]), end=int(pair[1]))


def _given(v) -> bool:
    return isinstance(v, str) and v != ""


def _groups(t: pd.DataFrame | None, key: str) -> dict:
    return dict(tuple(t.groupby(key))) if t is not None and len(t) else {}


def _country(code: str, n) -> C.CountryCount:
    th, en = COUNTRY_NAMES.get(code, (code, code))
    return C.CountryCount(code=code, name_th=th, name_en=en, articles=int(n))


def institution_files(cfg: dict, work: Path, code: dict[int, str], topic_group: dict[int, str]
                      ) -> tuple[dict[str, C._Model], dict[str, str], dict]:
    """({path: model}, {inst_key: published id}, KPI additions) — empty when the institutions step did not run."""
    inst = _opt(work / "15_institutions.parquet")
    meta = _meta(work / "15_institutions_meta.json")
    if inst is None or not meta:
        return {}, {}, {}
    icfg = cfg["institutions"]
    pub = inst[inst["published"].fillna(False).astype(bool)].sort_values(["articles", "code"], ascending=[False, True])
    iid = dict(zip(pub["inst_key"], pub["code"]))
    mix_by = _groups(_opt(work / "15_inst_topics.parquet"), "inst_key")
    years_by = _groups(_opt(work / "15_inst_years.parquet"), "inst_key")
    countries = _opt(work / "15_inst_countries.parquet")
    countries_by = _groups(countries[countries["inst_key"] != ""] if countries is not None else None, "inst_key")
    sugg_by = _groups(_opt(work / "15_inst_suggest.parquet"), "inst_key")
    pairs = _opt(work / "15_inst_pairs.parquet")
    pairs = pairs[pairs["a"].isin(list(iid)) & pairs["b"].isin(list(iid))] if pairs is not None else pd.DataFrame(
        columns=["a", "b", "articles"])
    both = pd.concat([pairs.rename(columns={"a": "k", "b": "o"}), pairs.rename(columns={"b": "k", "a": "o"})])
    partners_by = {k: g.sort_values(["articles", "o"], ascending=[False, True]).head(int(icfg["max_partners"]))
                   for k, g in both.groupby("k")} if len(both) else {}
    group_of = {}
    for k, g in mix_by.items():
        per = g.assign(group=g["topic_id"].astype(int).map(topic_group)).groupby("group")["count"].sum()
        group_of[k] = str(per.sort_values(ascending=False, kind="stable").index[0]) if len(per) else None

    rows, files = [], {}
    for r in pub.itertuples():
        k = r.inst_key
        rows.append(C.InstitutionSummary(
            id=r.code, name_th=r.name_th or "", name_en=r.name_en or "",
            type=r.type if r.type in INST_TYPES else "other",
            province=r.province if _given(r.province) else None, country=r.country if _given(r.country) else None,
            source=r.source, ror=r.ror if _given(r.ror) else "", articles=int(r.articles),
            articles_total=int(r.articles_total), articles_recent=int(r.articles_recent),
            intl_share=_f(r.intl_share), partners=int(r.partners), topics=int(r.topics), group=group_of.get(k)))
        mix, yrs, ptn = mix_by.get(k), years_by.get(k), partners_by.get(k)
        ctr, sug = countries_by.get(k), sugg_by.get(k)
        files[f"institutions/{r.code}.json"] = C.InstitutionDetail(
            id=r.code,
            years=[C.JournalYear(year=int(y.year), articles=int(y.articles)) for y in yrs.itertuples()]
            if yrs is not None else [],
            topics=[C.TopicShare(topic=code[int(t.topic_id)], count=int(t.count), share=_f(t.share) or 0.0)
                    for t in mix.head(int(icfg["top_topics"])).itertuples() if int(t.topic_id) in code]
            if mix is not None else [],
            partners=[C.Partner(id=iid[p.o], articles=int(p.articles)) for p in ptn.itertuples()]
            if ptn is not None else [],
            countries=[_country(c.country, c.articles) for c in ctr.itertuples()] if ctr is not None else [],
            suggested=[C.Suggestion(id=iid[s.other_key], similarity=_f(s.similarity) or 0.0,
                                    topics=[code[int(t)] for t in str(s.topics).split(";") if t and int(t) in code])
                       for s in sug.itertuples() if s.other_key in iid] if sug is not None else [])
    national = (countries[countries["inst_key"] == ""].sort_values(["articles", "country"], ascending=[False, True])
                if countries is not None else pd.DataFrame(columns=["country", "articles"]))
    P = provinces()
    used = sorted({p for p in pub["province"] if _given(p) and p in P})
    w = meta["windows"]
    files["institutions.json"] = C.InstitutionsFile(
        window=_window(w["W"]), recent=_window(w["R"]), min_articles=int(icfg["min_articles"]),
        network_min_articles=int(icfg["network_min_articles"]), articles_with_org=int(meta["with_org"]),
        pct_international=_f(meta.get("pct_international")), pct_multi_institution=_f(meta.get("pct_multi_institution")),
        sources={str(s): int(n) for s, n in (meta.get("sources") or {}).items()}, institutions=rows,
        edges=[C.CollabEdge(a=iid[e.a], b=iid[e.b], articles=int(e.articles)) for e in pairs.itertuples()],
        countries=[_country(c.country, c.articles) for c in national.itertuples()],
        province_names=[C.ProvinceName(code=p, name_th=P[p].name_th, name_en=P[p].name_en) for p in used])
    prov = _opt(work / "15_provinces.parquet")
    pct = lambda key: round(100 * float(meta[key]), 1) if meta.get(key) is not None else None  # noqa: E731
    kpis = {"institutions": int(meta["institutions_total"]), "pct_international": pct("pct_international"),
            "pct_multi_institution": pct("pct_multi_institution"),
            "provinces": int((prov["articles"] > 0).sum()) if prov is not None else None}
    return files, iid, kpis


def regions_file(cfg: dict, work: Path, iid: dict[str, str]) -> C.RegionsFile | None:
    prov = _opt(work / "15_provinces.parquet")
    meta = _meta(work / "15_institutions_meta.json")
    if prov is None or not meta:
        return None
    reg = _opt(work / "15_regions.parquet")
    inst = _opt(work / "15_institutions.parquet")
    located, with_org = int(meta["located"]), int(meta["with_org"])
    population = meta.get("population") or {}
    pop = population.get("by_code") or {}
    top: dict[str, list[str]] = {}
    if inst is not None:
        placed = inst[inst["inst_key"].isin(list(iid)) & inst["province"].map(_given)]
        for p, g in placed.groupby("province"):
            top[str(p)] = [iid[k] for k in g.sort_values(["articles", "inst_key"], ascending=[False, True])["inst_key"].head(3)]
    P = provinces()
    rows = [C.ProvinceStat(
        code=r.code, name_th=P[r.code].name_th, name_en=P[r.code].name_en, region=P[r.code].region,
        articles=int(r.articles), articles_recent=int(r.articles_recent),
        share=_f(r.articles / located) if located else None, institutions=int(r.institutions),
        per_100k=_f(100_000 * r.articles / pop[r.code], 2) if r.code in pop else None, top=top.get(r.code, []))
        for r in prov.itertuples() if r.code in P]
    regions = [C.RegionStat(key=x.region, articles=int(x.articles), share=_f(x.articles / located) if located else None)
               for x in reg.itertuples() if x.region in REGIONS] if reg is not None else []
    return C.RegionsFile(window=_window(meta["windows"]["W"]), articles_with_org=with_org, articles_located=located,
                         coverage=_f(located / with_org) if with_org else None,
                         population_year=population.get("year") if population else None, provinces=rows,
                         regions=regions)


def topic_sdg_numbers(work: Path) -> dict[int, list[int]]:
    """{topic id: SDG numbers} for Topic.sdg (framework "sdg" only)."""
    goals = _opt(work / "16_topic_goals.parquet")
    meta = _meta(work / "16_sdg_meta.json")
    if goals is None or not meta:
        return {}
    number = {g["id"]: int(g["number"]) for f in meta["frameworks"] if f["key"] == "sdg" for g in f["goals"]}
    s = goals[goals["goal_id"].isin(number)]
    return {int(t): sorted({number[g] for g in grp["goal_id"]}) for t, grp in s.groupby("topic_id")}


def sdg_file(cfg: dict, work: Path, code: dict[int, str]) -> C.SdgFile | None:
    goals = _opt(work / "16_topic_goals.parquet")
    meta = _meta(work / "16_sdg_meta.json")
    if goals is None or not meta:
        return None
    em = read_table(work / "07_emerging.parquet").set_index("topic_id")
    by_goal = _groups(goals, "goal_id")
    out = []
    for fw in meta["frameworks"]:
        for g in fw["goals"]:
            grp = by_goal.get(g["id"])
            tids = ([int(t) for t in grp.sort_values(["score", "topic_id"], ascending=[False, True])["topic_id"]]
                    if grp is not None else [])
            tids = [t for t in tids if t in code]
            sub = em.loc[[t for t in tids if t in em.index]]
            share_r = float(sub["share_recent"].sum()) if len(sub) else 0.0
            share_b = float(sub["share_baseline"].sum()) if len(sub) else 0.0
            out.append(C.GoalStat(id=g["id"], framework=fw["key"], number=int(g["number"]), th=g["th"], en=g["en"],
                                  topics=[code[t] for t in tids],
                                  articles_recent=int(sub["count_recent"].sum()) if len(sub) else 0,
                                  share_recent=round(share_r, 6),
                                  share_ratio=_f(share_r / share_b) if share_b > 0 else None))
    return C.SdgFile(method=meta["method"], version=str(meta["version"]),
                     frameworks=[C.FrameworkInfo(key=f["key"], th=f["th"], en=f["en"]) for f in meta["frameworks"]],
                     goals=out)


def global_file(cfg: dict, work: Path, code: dict[int, str], gcode: Callable[[int], str]) -> C.GlobalFile | None:
    meta = _meta(work / "17_benchmark_meta.json")
    table = _opt(work / "17_benchmark.parquet")
    if table is None or not meta or meta.get("skipped"):
        return None
    tax = _opt(work / "10_taxonomy.parquet")
    anchored = ({str(s): [code[int(t)] for t in sorted(g["topic_id"]) if int(t) in code]
                 for s, g in tax.groupby("subfield_id")} if tax is not None else {})
    bcfg = cfg["benchmark"]
    return C.GlobalFile(
        source=str(meta["source"]), country=str(meta["country"]), recent=_window(meta["recent"]),
        baseline=_window(meta["baseline"]), min_world_works=int(bcfg["min_world_works"]),
        min_world_ratio=float(bcfg["min_world_ratio"]), max_activity_index=float(bcfg["max_activity_index"]),
        subfields=[C.SubfieldBench(
            id=str(r.subfield_id), en=str(r.subfield_en), group=gcode(int(r.field_id)), world_recent=int(r.world_R),
            world_baseline=int(r.world_B), country_recent=int(r.country_R), country_baseline=int(r.country_B),
            tci_recent=int(r.tci_R), world_ratio=_f(r.world_ratio), activity_index=_f(r.activity_index),
            country_share=_f(r.country_share, 6), opportunity=bool(r.opportunity),
            topics=anchored.get(str(r.subfield_id), [])) for r in table.itertuples()])


def gaps_file(cfg: dict, work: Path, code: dict[int, str], iid: dict[str, str], jid: dict[str, str],
              jname: dict[str, str], gcode: Callable[[int], str]) -> C.GapsFile | None:
    meta = _meta(work / "18_gaps_meta.json")
    if not meta:
        return None
    few = _opt(work / "18_gap_few_institutions.parquet")
    bridges = _opt(work / "18_gap_bridges.parquet")
    world = _opt(work / "18_gap_world.parquet")
    conc = _opt(work / "18_concentration.parquet")
    inst = _opt(work / "15_institutions.parquet")
    inst_name = {r.inst_key: (r.name_th or r.name_en) for r in inst.itertuples()} if inst is not None else {}

    def top_of(kind: str, key: str) -> tuple[str, str]:
        if kind == "institution":                  # an institution without a page is neither linked nor named
            return (iid[key], inst_name.get(key, "")) if key in iid else ("", "")
        return jid.get(key, ""), jname.get(key) or journal_path(key)

    items = []
    for c in (conc.itertuples() if conc is not None else []):
        if c.scope == "topic" and int(c.unit) not in code:
            continue
        top, name = top_of(c.kind, str(c.top_key))
        items.append(C.Concentration(scope=c.scope, id=code[int(c.unit)] if c.scope == "topic" else gcode(int(c.unit)),
                                     kind=c.kind, articles=int(c.articles), hhi=_f(c.hhi) or 0.0,
                                     top_share=_f(c.top_share) or 0.0, top=top, top_name=name,
                                     concentrated=bool(c.concentrated)))
    g, r = cfg["gaps"], cfg["risk"]
    return C.GapsFile(
        recent=_window(meta["R"]), statuses=list(g["statuses"]), max_institutions=int(g["max_institutions"]),
        bridge_min_similarity=float(g["bridge_min_similarity"]), bridge_max_jaccard=float(g["bridge_max_jaccard"]),
        min_articles=int(r["min_articles"]), max_top_share=float(r["max_top_share"]), max_hhi=float(r["max_hhi"]),
        few_institutions=[C.FewInstitutions(topic=code[int(x.topic_id)], institutions=int(x.institutions))
                          for x in (few.itertuples() if few is not None else []) if int(x.topic_id) in code],
        bridges=[C.Bridge(a=code[int(b.s)], b=code[int(b.t)], similarity=_f(b.similarity) or 0.0, shared=int(b.shared),
                          jaccard=_f(b.jaccard) or 0.0)
                 for b in (bridges.itertuples() if bridges is not None else [])
                 if int(b.s) in code and int(b.t) in code],
        world=[C.WorldGap(subfield=str(x.subfield_id), en=str(x.subfield_en), world_ratio=_f(x.world_ratio),
                          activity_index=_f(x.activity_index),
                          topics=[code[int(t)] for t in str(x.topics).split(";") if t and int(t) in code])
               for x in (world.itertuples() if world is not None else [])],
        concentration=items)


def topic_institutions(work: Path, article_ids, labels_arr, iid: dict[str, str], max_n: int
                       ) -> dict[int, list[C.CountItem]] | None:
    """Top institutions per topic (canonical — alias/ROR merge spelling variants), linked when published (D6)."""
    links = _opt(work / "15_article_institutions.parquet")
    inst = _opt(work / "15_institutions.parquet")
    if links is None or inst is None:
        return None
    names = {r.inst_key: (r.name_th or r.name_en or r.inst_key) for r in inst.itertuples()}
    topic_of = pd.Series(labels_arr, index=article_ids)
    t = links.assign(topic_id=links["article_id"].map(topic_of)).dropna(subset=["topic_id"]).astype({"topic_id": int})
    c = (t[t["topic_id"] >= 0].groupby(["topic_id", "inst_key"]).size().rename("count").reset_index()
         .sort_values(["topic_id", "count", "inst_key"], ascending=[True, False, True]).groupby("topic_id").head(max_n))
    return {int(tid): [C.CountItem(key=names.get(k, k), count=int(n), id=iid.get(k))
                       for k, n in zip(g["inst_key"], g["count"])] for tid, g in c.groupby("topic_id")}


def skipped_modules(cfg: dict, work: Path) -> dict[str, str]:
    out = {}
    bench = _meta(work / "17_benchmark_meta.json")
    if bench.get("skipped"):
        out["global"] = str(bench["skipped"])
    if not cfg["institutions"]["enabled"]:
        out["institutions"] = out["regions"] = "institutions.enabled is false"
    if not cfg["sdg"]["enabled"]:
        out["sdg"] = "sdg.enabled is false"
    return out


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _and_list(names: list[str], word: str) -> str:
    """'a', 'a และ b', 'a, b และ c' (word = 'และ' / 'and')."""
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} {word} {names[-1]}"


def executive_summary(files: dict[str, C._Model]) -> C.ExecutiveSummary | None:
    """Policy sentences for the overview and the PDF brief, from the executives' files only — plain public
    language (example first, years written out, a unit on every number, no statistical terms)."""
    th: list[str] = []
    en: list[str] = []
    reg = files.get("regions.json")
    if reg is not None and reg.articles_located and reg.provinces:
        top = sorted(reg.provinces, key=lambda p: (-p.articles, p.code))[:5]
        w = reg.window
        th.append(f"บทความปี {w.start}–{w.end} มาจากสถาบันใน "
                  + _and_list([f"{p.name_th} ({p.articles:,} บทความ)" for p in top], "และ")
                  + f" มากที่สุด — นับจาก {reg.articles_located:,} บทความที่รู้จังหวัดของสถาบัน")
        en.append(f"Most articles of {w.start}–{w.end} come from institutions in "
                  + _and_list([f"{p.name_en} ({p.articles:,} articles)" for p in top], "and")
                  + f" — counted over the {reg.articles_located:,} articles whose institution's province is known")
    inst = files.get("institutions.json")
    if inst is not None and inst.pct_international is not None:
        cs, w = inst.countries[:3], inst.window
        th.append(f"ปี {w.start}–{w.end} มีบทความ {_pct(inst.pct_international)} ที่นักวิจัยจากต่างประเทศร่วมเขียน"
                  + (f" โดยร่วมกับ {_and_list([c.name_th for c in cs], 'และ')} บ่อยที่สุด" if cs else ""))
        en.append(f"{_pct(inst.pct_international)} of the articles of {w.start}–{w.end} were written with a "
                  "researcher from abroad"
                  + (f" — most often from {_and_list([c.name_en for c in cs], 'and')}" if cs else ""))
    sdg = files.get("sdg.json")
    goals = [g for g in sdg.goals if g.framework == "sdg"] if sdg is not None else []
    if goals:
        covered = sum(1 for g in goals if g.topics)
        missing = [g for g in goals if not g.topics][:3]
        th.append(f"หัวข้อวิจัยรอบนี้ตรงกับเป้าหมายการพัฒนาที่ยั่งยืน (SDG) {covered} จาก {len(goals)} ข้อ"
                  + (" ข้อที่ยังไม่มีหัวข้อใดตรงเลย เช่น " + ", ".join(f"SDG {g.number} {g.th}" for g in missing)
                     if missing else ""))
        en.append(f"This release's research topics match {covered} of the {len(goals)} Sustainable Development "
                  "Goals (SDGs)"
                  + ("; goals no topic matches yet include " + ", ".join(f"SDG {g.number} {g.en}" for g in missing)
                     if missing else ""))
    glob = files.get("global.json")
    opp = sorted((s for s in glob.subfields if s.opportunity), key=lambda s: (-(s.world_ratio or 0.0), s.id)) if glob else []
    if opp:
        names = _and_list([s.en for s in opp[:3]], "และ")
        names_en = _and_list([s.en for s in opp[:3]], "and")
        th.append(f"เช่น {names}: ทั่วโลกทำวิจัยเรื่องเหล่านี้เพิ่มขึ้นเร็ว แต่ไทยยังทำน้อย "
                  f"(สาขาแบบนี้มีทั้งหมด {len(opp)} สาขา)")
        en.append(f"For example {names_en}: research on these grows fast worldwide, but Thailand does little of it "
                  f"({len(opp)} such fields in all)")
    gaps = files.get("gaps.json")
    conc = [c for c in gaps.concentration if c.scope == "topic" and c.concentrated] if gaps else []
    risky = sorted({c.id for c in conc})
    if risky:
        tf = files.get("topics.json")
        name = {t.id: (t.th, t.en) for t in tf.topics} if tf is not None else {}
        ex = min(conc, key=lambda c: (-c.top_share, c.id))
        ex_th, ex_en = name.get(ex.id, ("", ""))
        th.append((f"เช่น “{ex_th}”: " if ex_th else "")
                  + f"{len(risky)} หัวข้อพึ่งสถาบันหรือวารสารแห่งเดียวเป็นหลัก (แหล่งเดียวมีบทความตั้งแต่ "
                  f"{_pct(gaps.max_top_share)} ของหัวข้อ หรือบทความกระจุกอยู่ในไม่กี่แหล่ง) "
                  "ถ้าแหล่งนั้นหยุด ตัวเลขของหัวข้อจะเปลี่ยนมาก")
        en.append((f"For example “{ex_en}”: " if ex_en else "")
                  + f"{len(risky)} topics rely mostly on one institution or journal (one source holds at least "
                  f"{_pct(gaps.max_top_share)} of the topic's articles, or the articles sit in only a few sources) — "
                  "if that source stops, the topic's numbers change a lot")
    return C.ExecutiveSummary(bullets_th=th, bullets_en=en) if th else None
