import json

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

