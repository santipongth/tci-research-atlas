"""Contract 2.1 files of the editors' release (P2), built from work/12_* (methods), 13_* (journals), 14_* (match)
and the previous release's snapshot (diff). Called by atlas.export_v2.build_release; each module is optional —
a missing checkpoint simply leaves its files (and its manifest.modules entry) out.

journals.json            every journal: identity (+ registry), counts, D2 completeness, D3 owner / in-house /
                         institutions / foreign share, group; special-issue topics (D5)
journals/<id>.json       years, topic mix (top journals.top_topics), scope drift (D1), gained/lost topics, peers
                         (D4), completeness by element (D2), methods mix (D7), special-issue opportunities (D5)
methods.json             lexicon, corpus shares, shares by year, per-topic shares + sample size + monoculture (E11)
match.json               the 'match my abstract' index (R3/R4) with published ids
Only aggregates are published; no abstract, no person.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from atlas.io_utils import json_float, read_optional, read_table
from atlas.methods import METHODS
from atlas.schema import contract as C


def _window(pair) -> C.YearWindow:
    return C.YearWindow(start=int(pair[0]), end=int(pair[1]))


def _int_or_none(v) -> int | None:
    return int(v) if v is not None and pd.notna(v) else None


def _topic_years(t, code: dict, min_articles: int) -> C.JournalTopicYears | None:
    """13_journal_topic_years rows of one journal → per-year shares of its largest topics (None: not published)."""
    if t is None or t.empty:
        return None
    wide = t.pivot(index="year", columns="topic_id", values="share").sort_index()
    years = [int(y) for y in wide.index]
    articles = t.drop_duplicates("year").set_index("year")["articles"].reindex(wide.index).astype(int).tolist()
    order = t.drop_duplicates("topic_id")["topic_id"].astype(int).tolist()       # largest first, as the step wrote them
    return C.JournalTopicYears(
        years=years, articles=articles, min_articles=min_articles,
        topics=[C.JournalTopicLine(topic=code[tid], shares=[json_float(v) for v in wide[tid]]) for tid in order
                if tid != -1 and tid in code],
        other=[json_float(v) for v in wide[-1]] if -1 in wide.columns else [None] * len(years))


def journal_files(cfg: dict, work: Path, code: dict[int, str], topic_group: dict[int, str]
                  ) -> tuple[dict[str, C._Model], dict[str, str], dict[str, str]]:
    """({path: model}, {journal_key: id}, {journal_key: display name}) — empty when the journals step did not run."""
    summary = read_optional(work / "13_journals.parquet")
    if summary is None:
        return {}, {}, {}
    jcfg = cfg["journals"]
    meta = json.loads((work / "13_journals_meta.json").read_text(encoding="utf-8"))
    mix = read_table(work / "13_journal_topics.parquet")
    mix = mix[mix["topic_id"].astype(int).isin(list(code))]
    jid = dict(zip(summary["journal_key"], summary["code"]))
    names = {r.journal_key: (r.name_th or r.name_en or r.path) for r in summary.itertuples()}
    by = {name: t.groupby("journal_key") for name, t in {
        "years": read_table(work / "13_journal_years.parquet"), "mix": mix,
        "drift": read_table(work / "13_journal_drift.parquet"), "shifts": read_table(work / "13_journal_shifts.parquet"),
        "peers": read_table(work / "13_journal_peers.parquet"),
        "comp": read_table(work / "13_journal_completeness.parquet"),
        "methods": read_table(work / "13_journal_methods.parquet"),
        "opps": read_table(work / "13_journal_opportunities.parquet"),
        "tyears": read_table(work / "13_journal_topic_years.parquet")}.items()}
    groups = {k: dict(tuple(g)) for k, g in by.items()}
    group_of = {}
    for jk, g in groups["mix"].items():
        per = g.assign(group=g["topic_id"].astype(int).map(topic_group)).groupby("group")["count"].sum()
        group_of[jk] = str(per.sort_values(ascending=False).index[0]) if len(per) else None

    rows, files = [], {}
    for r in summary.itertuples():
        jk = r.journal_key
        rows.append(C.JournalSummary(
            id=r.code, key=jk, path=r.path, name_th=r.name_th or "", name_en=r.name_en or "", issn=r.issn or "",
            eissn=r.eissn or "", tci_tier=_int_or_none(r.tci_tier), tci_field=r.tci_field or "",
            publisher=r.publisher or "", url=r.url or "", in_registry=bool(r.in_registry), articles=int(r.articles),
            articles_window=int(r.articles_window), articles_recent=int(r.articles_recent),
            first_year=_int_or_none(r.first_year), last_year=_int_or_none(r.last_year), active=bool(r.active),
            low_data=bool(r.low_data), group=group_of.get(jk), completeness=json_float(r.completeness, 1),
            owner=r.owner_name or "", owner_source=r.owner_source if r.owner_source in ("registry", "inferred") else None,
            owner_matched=bool(r.owner_matched), inhouse_share=json_float(r.inhouse_share), n_orgs=int(r.n_orgs),
            effective_orgs=json_float(r.effective_orgs, 2), foreign_share=json_float(r.foreign_share),
            affiliation_coverage=json_float(r.affiliation_coverage), methods_coverage=json_float(r.methods_coverage)))
        g = {k: v.get(jk) for k, v in groups.items()}
        topics = g["mix"].head(int(jcfg["top_topics"])) if g["mix"] is not None else None
        shifts = g["shifts"]
        files[f"journals/{r.code}.json"] = C.JournalDetail(
            id=r.code,
            years=[C.JournalYear(year=int(y.year), articles=int(y.articles)) for y in g["years"].itertuples()]
            if g["years"] is not None else [],
            topics=[C.TopicShare(topic=code[int(t.topic_id)], count=int(t.count), share=json_float(t.share) or 0.0)
                    for t in topics.itertuples()] if topics is not None else [],
            drift=[C.DriftPoint(year=int(d.year), articles=int(d.articles), distance=json_float(d.distance))
                   for d in g["drift"].itertuples()] if g["drift"] is not None else [],
            gained=[C.TopicShift(topic=code[int(s.topic_id)], share_before=json_float(s.share_before) or 0.0,
                                 share_after=json_float(s.share_after) or 0.0)
                    for s in shifts.itertuples() if s.kind == "gained" and int(s.topic_id) in code]
            if shifts is not None else [],
            lost=[C.TopicShift(topic=code[int(s.topic_id)], share_before=json_float(s.share_before) or 0.0,
                               share_after=json_float(s.share_after) or 0.0)
                  for s in shifts.itertuples() if s.kind == "lost" and int(s.topic_id) in code]
            if shifts is not None else [],
            peers=[C.Peer(id=jid[p.peer_key], similarity=json_float(p.similarity) or 0.0) for p in g["peers"].itertuples()]
            if g["peers"] is not None else [],
            completeness=[C.CompletenessItem(key=c.component, rate=json_float(c.rate), n=int(c.n))
                          for c in g["comp"].itertuples()] if g["comp"] is not None else [],
            methods=[C.MethodShare(method=m.method, count=int(m.count), share=json_float(m.share) or 0.0)
                     for m in g["methods"].sort_values(["count", "method"], ascending=[False, True]).itertuples()]
            if g["methods"] is not None else [],
            opportunities=[C.JournalOpportunity(topic=code[int(o.topic_id)], reason=o.reason,
                                                journal_articles=int(o.journal_articles), hosts=int(o.hosts))
                           for o in g["opps"].itertuples() if int(o.topic_id) in code] if g["opps"] is not None else [],
            topic_years=_topic_years(g["tyears"], code, int(jcfg["year_mix_min_articles"])))
    si = read_table(work / "13_special_issue.parquet")
    w = meta["windows"]
    files["journals.json"] = C.JournalsFile(
        window=_window(w["W"]), recent=_window(w["R"]), baseline=_window(w["B"]),
        min_articles=int(jcfg["min_articles"]), completeness_weights=dict(jcfg["completeness_weights"]),
        inhouse_flag_share=jcfg["inhouse_flag_share"], special_issue_statuses=list(jcfg["special_issue_statuses"]),
        special_issue_max_hosts=int(jcfg["special_issue_max_hosts"]),
        special_issue_min_host_articles=int(jcfg["special_issue_min_host_articles"]),
        drift_reference_years=int(jcfg["drift_reference_years"]), journals=rows,
        special_issue=[C.SpecialIssueTopic(topic=code[int(s.topic_id)], hosts=int(s.hosts),
                                           top_host_share=json_float(s.top_host_share) or 0.0, articles_recent=int(s.articles_R))
                       for s in si.itertuples() if int(s.topic_id) in code])
    return files, jid, names


def methods_file(cfg: dict, work: Path, code: dict[int, str]) -> C.MethodsFile | None:
    topics = read_optional(work / "12_methods_topics.parquet")
    if topics is None or not (work / "12_methods_meta.json").exists():
        return None
    mcfg = cfg["methods"]
    meta = json.loads((work / "12_methods_meta.json").read_text(encoding="utf-8"))
    notes = read_optional(work / "12_methods_notes.parquet")
    note = ({int(n.topic_id): C.Narrative(th=str(n.th), en=str(n.en), source=str(n.source)) for n in notes.itertuples()}
            if notes is not None else {})

    def shares(counts: dict, n_with: int) -> list[C.MethodShare]:
        items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [C.MethodShare(method=k, count=int(n), share=round(n / n_with, 4) if n_with else 0.0) for k, n in items]

    by = meta["by_year"]
    return C.MethodsFile(
        lexicon_version=meta["lexicon_version"], window=_window(meta["window"]), articles=int(meta["articles"]),
        with_methods=int(meta["with_methods"]), monoculture_methods=list(mcfg["monoculture_methods"]),
        monoculture_min_share=float(mcfg["monoculture_min_share"]), monoculture_share=json_float(meta.get("monoculture_share")),
        min_articles=int(mcfg["min_articles"]), methods=[C.MethodInfo(key=m.key, th=m.th, en=m.en) for m in METHODS],
        corpus=shares(meta["counts"], int(meta["with_methods"])),
        by_year=C.MethodYears(years=by["years"], articles=by["articles"], shares=by["shares"]),
        topics=[C.TopicMethods(
            topic=code[int(t.topic_id)], articles=int(t.articles), with_methods=int(t.with_methods),
            coverage=json_float(t.coverage) or 0.0, methods=shares(json.loads(t.counts), int(t.with_methods)),
            sample_size_n=int(t.ss_n), sample_size_median=json_float(t.ss_median, 1), sample_size_q1=json_float(t.ss_q1, 1),
            sample_size_q3=json_float(t.ss_q3, 1), monoculture_share=json_float(t.monoculture_share), monoculture=bool(t.monoculture),
            note=note.get(int(t.topic_id)))
            for t in topics.itertuples() if int(t.topic_id) in code])


def match_file(work: Path, code: dict[int, str], jid: dict[str, str]) -> C.MatchIndex | None:
    p = work / "14_match.json"
    if not p.exists():
        return None
    ix = json.loads(p.read_text(encoding="utf-8"))
    return C.MatchIndex(
        analyzer=ix["analyzer"], fold=ix["fold"], docs=ix["docs"], max_terms=ix["max_terms"],
        min_similarity=ix["min_similarity"], fit_topics=ix["fit_topics"], min_query_chars=ix["min_query_chars"],
        grams=ix["grams"], idf=ix["idf"],
        topics=[C.MatchTopic(id=code[int(t["topic_id"])], terms=t["terms"], weights=t["weights"])
                for t in ix["topics"] if int(t["topic_id"]) in code],
        journals=[C.MatchJournal(id=jid[j["journal_key"]], topics=[code[int(t)] for t in j["topics"] if int(t) in code],
                                 shares=[s for t, s in zip(j["topics"], j["shares"]) if int(t) in code])
                  for j in ix["journals"] if j["journal_key"] in jid])
