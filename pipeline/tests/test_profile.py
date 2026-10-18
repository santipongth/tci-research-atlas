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


def test_render_markdown_mentions_key_numbers(thaijo_dir):
    md = render_markdown(profile_corpus(thaijo_dir))
    assert md.startswith("# รายงานคุณภาพคลังบทความ")
    assert "11" in md and "BECJournal" in md


def test_cli_profile_writes_json(thaijo_dir, tmp_path):
    out = tmp_path / "r.json"
    res = CliRunner().invoke(app, ["profile", str(thaijo_dir), "--out", str(out)])
    assert res.exit_code == 0, res.stdout
    assert json.loads(out.read_text(encoding="utf-8"))["files"] == 11
