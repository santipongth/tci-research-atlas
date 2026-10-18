import json

import pandas as pd
from typer.testing import CliRunner

from atlas.cli import app
from atlas.profile import profile_corpus, render_markdown


def test_profile_real_fixtures(thaijo_dir):
    r = profile_corpus(thaijo_dir)
    assert (r["files"], r["unique_articles"], r["duplicate_files"]) == (11, 11, 0)
    assert (r["years"]["min"], r["years"]["max"], r["years"]["missing"]) == (2013, 2018, 0)
    assert r["years"]["by_source"] == {"published": 9, "doi": 2}
    cov = r["coverage_pct"]
    assert cov["title_en"] == 100.0 and cov["abstract_en"] == 90.9
    assert cov["references"] == 63.6 and cov["self_citation_only"] == 45.5
    assert r["text_quality"] == {"thai_pua_repaired": 1, "stat_symbols_missing": 1}
    assert r["journals"]["count"] == 1


def test_profile_year_totals_and_forward_dated(thaijo_dir, tmp_path):
    import re
    import shutil
    from datetime import date

    r = profile_corpus(thaijo_dir)
    assert r["years"]["forward_dated"] == 0
    totals = {e["year"]: e for e in r["year_totals"]}
    assert sum(e["articles"] for e in totals.values()) == 11
    first = min(totals)
    assert totals[first]["vs_prev"] is None
    for y, e in totals.items():
        prev = totals.get(y - 1)
        if prev:
            assert e["vs_prev"] == round(e["articles"] / prev["articles"], 3)

    src = tmp_path / "in"
    src.mkdir()
    for f in sorted(thaijo_dir.glob("*.md"))[:2]:
        shutil.copyfile(f, src / f.name)
    future = sorted(src.glob("*.md"))[0]
    text = future.read_text(encoding="utf-8")
    future.write_text(re.sub(r"\*\*Published:\*\* .*", f"**Published:** {date.today().year + 1}-01-15", text),
                      encoding="utf-8")
    r2 = profile_corpus(src)
    assert r2["years"]["forward_dated"] == 1
    md = render_markdown(r2)
    assert "Forward-dated" in md and "Articles per year" in md


def test_render_markdown_mentions_key_numbers(thaijo_dir):
    md = render_markdown(profile_corpus(thaijo_dir))
    assert md.startswith("# รายงานคุณภาพคลังบทความ")
    assert "11" in md and "BECJournal" in md


def test_cli_profile_writes_json(thaijo_dir, tmp_path):
    out = tmp_path / "r.json"
    res = CliRunner().invoke(app, ["profile", str(thaijo_dir), "--out", str(out)])
    assert res.exit_code == 0, res.stdout
    assert json.loads(out.read_text(encoding="utf-8"))["files"] == 11


def _md(title: str, view: int, doi: str) -> str:
    return (f"# {title}\n\n**Journal:** J\n**Published:** 2020-01-01\n"
            f"**Article URL:** https://so01.tci-thaijo.org/index.php/J/article/view/{view}\n\n"
            f"## Abstract\n\nAn English abstract for testing.  DOI: {doi}\n")


def test_profile_reports_doi_collisions_with_different_titles(tmp_path):
    (tmp_path / "a.md").write_text(_md("Rice yield under drought", 1, "10.1234/j.2020.1"), encoding="utf-8")
    (tmp_path / "b.md").write_text(_md("Tourism in Nan province", 2, "10.1234/j.2020.1"), encoding="utf-8")
    (tmp_path / "c.md").write_text(_md("Unrelated third paper", 3, "10.1234/j.2020.3"), encoding="utf-8")
    r = profile_corpus(tmp_path)
    col = r["doi_title_collisions"]
    assert col["count"] == 1 and len(col["examples"]) == 1
    ex = col["examples"][0]
    assert ex["doi"] == "10.1234/j.2020.1" and sorted(ex["article_ids"]) == ["so01:J:1", "so01:J:2"]
    assert "DOI collisions" in render_markdown(r)


def test_profile_reports_files_with_errors_and_replaced_bytes(thaijo_dir, tmp_path):
    import shutil

    raw = (thaijo_dir / "so02_BECJournal_54895.md").read_bytes()
    (tmp_path / "broken_bytes.md").write_bytes(raw.replace(b"## Abstract\n", b"## Abstract\n\x80\x81 ", 1))
    shutil.copyfile(thaijo_dir / "so02_BECJournal_62642.md", tmp_path / "clean.md")
    (tmp_path / "bad.md").mkdir()
    r = profile_corpus(tmp_path)
    assert r["files"] == 2 and r["text_quality"]["decode_replaced"] == 1
    assert r["files_with_errors"]["count"] == 1 and r["files_with_errors"]["examples"][0]["path"].endswith("bad.md")
    assert "Files with errors" in render_markdown(r)


# ---- Task 20 items 1 and 5
def test_profile_reports_error_ratio_and_warns_above_threshold(tmp_path):
    for i in range(3):
        (tmp_path / f"g{i}.md").write_text(_md(f"Paper {i}", i, f"10.1/{i}"), encoding="utf-8")
    (tmp_path / "bad.md").mkdir()
    r = profile_corpus(tmp_path)                     # does not raise: it is the inspection tool
    fe = r["files_with_errors"]
    assert fe["count"] == 1 and fe["ratio"] == 0.25 and fe["threshold"] == 0.01
    assert "\N{WARNING SIGN}" in render_markdown(r)
    ok = profile_corpus(tmp_path, max_error_ratio=0.5)
    assert "\N{WARNING SIGN}" not in render_markdown(ok)


def test_doi_title_collisions_exact_output():
    from atlas.profile import doi_title_collisions

    arts = pd.DataFrame({
        "article_id": ["a", "b", "c", "d", "e", "f"],
        "doi": ["10.1/X", "10.1/x ", "10.2/y", "10.2/y", "10.3/z", ""],
        "title_th": ["", "", "Same title", "Same title", "", ""],
        "title_en": ["Rice yield", "Tourism in Nan", "", "", "Solo", "No doi"]})
    r = doi_title_collisions(arts)
    assert r == {"count": 1, "examples": [{"doi": "10.1/x", "titles": ["Rice yield", "Tourism in Nan"],
                                           "article_ids": ["a", "b"]}]}
    assert doi_title_collisions(arts, max_examples=0) == {"count": 1, "examples": []}


def test_doi_title_collisions_is_fast_on_250k_scale():
    import time

    from atlas.profile import doi_title_collisions

    n = 50_000
    arts = pd.DataFrame({"article_id": [f"id{i}" for i in range(n)], "doi": [f"10.1/{i}" for i in range(n)],
                         "title_th": "", "title_en": [f"Title number {i}" for i in range(n)]})
    t0 = time.perf_counter()
    assert doi_title_collisions(arts)["count"] == 0
    assert time.perf_counter() - t0 < 3.0
