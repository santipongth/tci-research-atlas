"""Journal metrics for editors (D2 metadata completeness, D3 in-house / diversity / foreign authors).

Aggregates per journal only — author rows are read internally and never published (PDPA).

completeness     per metadata element (config.COMPLETENESS_COMPONENTS) the share of a journal's window articles
                 that have it, and a 0–100 score = weighted mean of the known rates (journals.completeness_weights,
                 renormalised over the elements that have a rate). The elements follow the TCI assessment's
                 metadata items; the score is NOT the official TCI assessment.
                 refs_romanized is known only for articles that cite Thai-language sources (a "how to cite
                 this article" line is not one); affiliations only for articles with author rows. An element the
                 whole corpus lacks (no column, all blank, no reference rows) is unknown and drops out of the weights.
owner            registry publisher_org (source "registry"), else the organisation on most articles (source
                 "inferred", only when it signs ≥ journals.owner_min_share of them) — inferences are labelled.
inhouse_share    share of articles with ≥ 1 author from the owner, among articles with ≥ 1 recognised organisation;
                 null when the owner is not found among the authors (owner_matched false)
effective_orgs   1 / Σ p² of the organisations' article shares ("as diverse as N equal institutions")
foreign_share    share of articles with ≥ 1 affiliation outside Thailand (atlas.countries), same denominator
affiliation_coverage  share of window articles with ≥ 1 recognised organisation (that denominator)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from atlas.config import COMPLETENESS_COMPONENTS
from atlas.countries import is_foreign_affiliation
from atlas.io_utils import text_column
from atlas.orgs import org_key
from atlas.thai import thai_ratio

AUTHOR_METRIC_COLUMNS = ["journal_key", "with_org", "affiliation_coverage", "inhouse_share", "n_orgs",
                         "effective_orgs", "foreign_share"]
OWNER_COLUMNS = ["journal_key", "owner_key", "owner_name", "owner_source", "owner_share", "owner_matched"]


def _text(df: pd.DataFrame, col: str) -> pd.Series:
    return text_column(df, col).str.strip()


def _flag(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].fillna(False).astype(bool) if col in df.columns else pd.Series(False, index=df.index)


def article_completeness(arts: pd.DataFrame, refs: pd.DataFrame, authors: pd.DataFrame) -> pd.DataFrame:
    """article_id + one nullable-boolean column per component (NA = not applicable / unknown)."""
    out = pd.DataFrame({"article_id": arts["article_id"].to_numpy()})
    unknown = pd.array([pd.NA] * len(out), dtype="boolean")
    for col in ("abstract_en", "title_en", "keywords_en", "doi"):
        # a column missing (or blank) for the whole corpus means the source never carried it: unknown, not 0 %
        has = _text(arts, col) != ""
        out[col] = pd.array(has.to_numpy(), dtype="boolean") if has.any() else unknown
    if "has_references" in arts.columns and len(refs):      # no reference rows at all (table input) → unknown
        out["references"] = pd.array((_flag(arts, "has_references") & ~_flag(arts, "self_citation_only")).to_numpy(),
                                     dtype="boolean")
    else:
        out["references"] = unknown
    ids = out["article_id"]
    own_refs = refs[~_flag(refs, "self_citation")] if len(refs) else refs   # "how to cite this article" is no source
    thai_refs = set(own_refs.loc[_text(own_refs, "lang") == "th", "article_id"]) if len(own_refs) else set()
    translated = set(own_refs.loc[_flag(own_refs, "translated"), "article_id"]) if len(own_refs) else set()
    out["refs_romanized"] = pd.array([(a in translated) if a in thai_refs else pd.NA for a in ids], dtype="boolean")
    if len(authors):
        has = (_text(authors, "affiliation_th") != "") | (_text(authors, "affiliation_en") != "")
        every = has.groupby(authors["article_id"]).all()
        out["affiliations"] = pd.array([bool(every[a]) if a in every.index else pd.NA for a in ids], dtype="boolean")
    else:
        out["affiliations"] = pd.array([pd.NA] * len(out), dtype="boolean")
    return out[["article_id", *COMPLETENESS_COMPONENTS]]


def completeness_table(comp: pd.DataFrame, journal_of: pd.Series, weights: dict[str, float]
                       ) -> tuple[pd.DataFrame, pd.Series]:
    """(long table journal_key, component, rate, n — rate null when n = 0; score per journal 0–100 or NaN).
    journal_of: article_id → journal_key."""
    c = comp.assign(journal_key=comp["article_id"].map(journal_of)).dropna(subset=["journal_key"])
    c = c[c["journal_key"].astype(str) != ""]
    rows = []
    for col in COMPLETENESS_COMPONENTS:
        v = c[col].astype("Float64")
        g = v.groupby(c["journal_key"])
        rate, n = g.mean(), g.count()
        rows.append(pd.DataFrame({"journal_key": n.index, "component": col, "rate": rate.reindex(n.index).to_numpy(
            dtype=float, na_value=np.nan), "n": n.to_numpy(dtype=int)}))
    long = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["journal_key", "component", "rate", "n"])
    w = long["component"].map(weights).fillna(0.0)
    known = long["rate"].notna() & (w > 0)
    num = (long["rate"].where(known, 0.0) * w).groupby(long["journal_key"]).sum()
    den = w.where(known, 0.0).groupby(long["journal_key"]).sum()
    score = (100 * num / den.replace(0.0, np.nan)).round(1)
    return long, score


def owner_key_of(name: str) -> str:
    """org_key of a registry publisher name (Thai or English as written)."""
    name = name or ""
    return org_key(name, "") if thai_ratio(name) > 0.5 else org_key("", name)


def _orgs(arts: pd.DataFrame, authors: pd.DataFrame) -> pd.DataFrame:
    """Distinct (article_id, journal_key, org_key) for articles of `arts` (author rows with an org_key)."""
    if not len(authors):
        return pd.DataFrame(columns=["article_id", "journal_key", "org_key"])
    a = authors.loc[_text(authors, "org_key") != "", ["article_id", "org_key"]].drop_duplicates()
    return a.merge(arts[["article_id", "journal_key"]], on="article_id")


def owners(arts: pd.DataFrame, authors: pd.DataFrame, registry_owner: dict[str, str], min_share: float,
           display: dict[str, str]) -> pd.DataFrame:
    """One row per journal of `arts`: the owner organisation, how it is known, and the share of the journal's
    articles (with a recognised organisation) that it signs. display: org_key → written name."""
    orgs = _orgs(arts, authors)
    with_org = orgs.groupby("journal_key")["article_id"].nunique()
    per = orgs.groupby(["journal_key", "org_key"])["article_id"].nunique().rename("n").reset_index()
    by_journal = dict(tuple(per.groupby("journal_key")))           # one pass, not one filter per journal
    empty = per.iloc[0:0]
    rows = []
    for jk in sorted(arts["journal_key"].unique()):
        denom = int(with_org.get(jk, 0))
        mine = by_journal.get(jk, empty)
        reg = (registry_owner.get(jk) or "").strip()
        if reg:
            key = owner_key_of(reg)
            n = int(mine.loc[mine["org_key"] == key, "n"].sum()) if key else 0
            rows.append({"journal_key": jk, "owner_key": key, "owner_name": reg, "owner_source": "registry",
                         "owner_share": n / denom if denom else np.nan, "owner_matched": n > 0})
            continue
        if denom == 0 or mine.empty:
            rows.append({"journal_key": jk, "owner_key": "", "owner_name": "", "owner_source": None,
                         "owner_share": np.nan, "owner_matched": False})
            continue
        top = mine.sort_values(["n", "org_key"], ascending=[False, True]).iloc[0]
        share = int(top["n"]) / denom
        ok = share >= min_share
        rows.append({"journal_key": jk, "owner_key": top["org_key"] if ok else "",
                     "owner_name": display.get(top["org_key"], top["org_key"]) if ok else "",
                     "owner_source": "inferred" if ok else None, "owner_share": share if ok else np.nan,
                     "owner_matched": ok})
    return pd.DataFrame(rows, columns=OWNER_COLUMNS)


def author_metrics(arts: pd.DataFrame, authors: pd.DataFrame, owner_df: pd.DataFrame) -> pd.DataFrame:
    """In-house share, institutional diversity and foreign-author share per journal (articles of `arts`)."""
    orgs = _orgs(arts, authors)
    total = arts.groupby("journal_key")["article_id"].nunique()
    with_org = orgs.groupby("journal_key")["article_id"].nunique()
    foreign_ids: set = set()
    if len(authors):
        aff = authors[["article_id", "affiliation_th", "affiliation_en"]].copy()
        aff[["affiliation_th", "affiliation_en"]] = aff[["affiliation_th", "affiliation_en"]].fillna("").astype(str)
        pairs = aff[["affiliation_th", "affiliation_en"]].drop_duplicates()
        pairs = pairs.assign(foreign=[is_foreign_affiliation(t, e) for t, e in
                                      zip(pairs["affiliation_th"], pairs["affiliation_en"])])
        fa = aff.merge(pairs, on=["affiliation_th", "affiliation_en"], how="left")
        foreign_ids = set(fa.loc[fa["foreign"].fillna(False).astype(bool), "article_id"])
    # the in-house share is reported only when the owner was found among the authors (matched); an owner the
    # data never mentions would otherwise read as "0 % in-house" instead of "unknown"
    matched = owner_df.set_index("journal_key")["owner_matched"].fillna(False).astype(bool)
    owner_of = {jk: k for jk, k in owner_df.set_index("journal_key")["owner_key"].items() if matched.get(jk, False)}
    by_journal = dict(tuple(orgs.groupby("journal_key")))
    empty = orgs.iloc[0:0]
    rows = []
    for jk, n_all in total.items():
        mine = by_journal.get(jk, empty)
        denom = int(with_org.get(jk, 0))
        counts = mine.groupby("org_key")["article_id"].nunique()
        p = counts / counts.sum() if counts.sum() else counts
        okey = owner_of.get(jk, "")
        inhouse = mine.loc[mine["org_key"] == okey, "article_id"].nunique() if okey else None
        arts_with_org = set(mine["article_id"])
        rows.append({
            "journal_key": jk, "with_org": denom, "affiliation_coverage": denom / int(n_all) if n_all else np.nan,
            "inhouse_share": inhouse / denom if (inhouse is not None and denom) else np.nan,
            "n_orgs": int(len(counts)), "effective_orgs": float(1.0 / (p ** 2).sum()) if len(p) else np.nan,
            "foreign_share": len(arts_with_org & foreign_ids) / denom if denom else np.nan,
        })
    return pd.DataFrame(rows, columns=AUTHOR_METRIC_COLUMNS)
