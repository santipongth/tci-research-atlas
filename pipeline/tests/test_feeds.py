"""Atom feeds written by `atlas publish --site` (P4, Ruling 9) — built only from the release folders on the site."""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from atlas.config import load_config
from atlas.feeds import write_feeds
from atlas.narrative import STATUS_TH
from atlas.publish import publish_site

A = "{http://www.w3.org/2005/Atom}"
URL = "https://example.github.io/atlas"
RICE = "\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER WO WAEN}"


def _topic(tid, status="STABLE", th="t", en="t", n=40, growth=0.12):
    return {"id": tid, "th": th, "en": en, "status": status, "metrics": {"count_recent": n, "share_growth": growth}}


def _release(root: Path, rel: str, topics: list[dict], headline: tuple[str, str] | None = None,
             diff: dict | None = None) -> Path:
    d = root / rel
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"release": rel, "generated_at": f"2026-0{rel[-1]}-01T00:00:00+00:00"}),
                                     encoding="utf-8")
    ov = {"release": rel, "kpis": {"articles": 1234, "topics": len(topics)}}
    if headline:
        ov["brief"] = {"headline_th": headline[0], "headline_en": headline[1]}
    (d / "overview.json").write_text(json.dumps(ov, ensure_ascii=False), encoding="utf-8")
    (d / "topics.json").write_text(json.dumps({"topics": topics}, ensure_ascii=False), encoding="utf-8")
    if diff is not None:
        (d / "diff.json").write_text(json.dumps(diff), encoding="utf-8")
    return d


def _site(tmp_path, releases):
    site = tmp_path / "site"
    for rel, topics, extra in releases:
        _release(site / "data", rel, topics, **extra)
    return site


def _entries(path: Path):
    root = ET.parse(path).getroot()
    assert root.tag == f"{A}feed"
    return root, root.findall(f"{A}entry")


def test_feeds_are_valid_atom_and_escape_markup_in_thai_and_english(tmp_path):
    th, en = f"{RICE} & <{RICE}>", "Rice & <water> > salt"
    site = _site(tmp_path, [
        ("2026Q1", [_topic("T000001", th=th, en=en)], {}),
        ("2026Q2", [_topic("T000001", "EMERGING", th=th, en=en, growth=None)],
         {"headline": (f"{RICE} <b> & co", "Growth & <decline>"),
          "diff": {"previous_release": "2026Q1", "new_topics": [{}, {}], "retired": [{}], "status_changes": [{}]}}),
    ])
    r = write_feeds(site, URL, 12)
    feeds = site / "data" / "feeds"
    root, entries = _entries(feeds / "releases.xml")
    assert root.find(f"{A}id").text == f"{URL}/data/feeds/releases.xml"
    assert root.find(f"{A}updated").text == "2026-02-01T00:00:00+00:00"            # newest manifest generated_at
    assert [e.find(f"{A}title").text for e in entries] == ["2026Q2", "2026Q1"]
    assert entries[0].find(f"{A}link").get("href") == f"{URL}/#/topics"
    summary = entries[0].find(f"{A}summary").text
    assert f"{RICE} <b> & co" in summary and "Growth & <decline>" in summary
    assert "2 new topics" in summary and "1 gone" in summary and "1 changed status" in summary
    assert "EMERGING" not in summary and "2026Q1" in summary
    assert "1,234 articles" in entries[1].find(f"{A}summary").text                 # no brief → KPI line
    raw = (feeds / "topics" / "T000001.xml").read_text(encoding="utf-8")
    assert "&amp;" in raw and "&lt;water&gt;" in raw and "<water>" not in raw
    troot, tent = _entries(feeds / "topics" / "T000001.xml")
    assert troot.find(f"{A}title").text == f"TCI Research Atlas — {th} / {en}"
    assert [e.find(f"{A}title").text for e in tent] == [f"2026Q2: {STATUS_TH['EMERGING']} / Emerging",
                                                        f"2026Q1: {STATUS_TH['STABLE']} / Stable"]
    assert tent[0].find(f"{A}link").get("href") == f"{URL}/#/topics/T000001"
    assert "trend not yet known" in tent[0].find(f"{A}summary").text and "n/a" not in tent[0].find(f"{A}summary").text
    assert "40 recent articles" in tent[1].find(f"{A}summary").text                  # no window given: no years
    assert "+12.0%" in tent[1].find(f"{A}summary").text
    assert r == {"releases": str(feeds / "releases.xml"), "topics": 1, "entries": 2}


def test_newest_first_and_at_most_max_entries(tmp_path):
    rels = ["2025Q4", "2026Q2", "2026Q1", "2026Q3"]                               # folder order is not release order
    site = _site(tmp_path, [(r, [_topic("T000001")], {}) for r in rels])
    (site / "data" / "notarelease").mkdir()                                        # ignored: not a release name
    write_feeds(site, URL + "/", 3)
    _, entries = _entries(site / "data" / "feeds" / "releases.xml")
    assert [e.find(f"{A}title").text for e in entries] == ["2026Q3", "2026Q2", "2026Q1"]
    _, tent = _entries(site / "data" / "feeds" / "topics" / "T000001.xml")
    assert len(tent) == 3


def test_one_topic_feed_per_topic_of_the_newest_release(tmp_path):
    site = _site(tmp_path, [
        ("2026Q1", [_topic("T000001"), _topic("T000003")], {}),
        ("2026Q2", [_topic("T000001"), _topic("T000002"), {"id": "../bad", "th": "x"}], {}),
    ])
    stale = site / "data" / "feeds" / "topics" / "T000009.xml"
    stale.parent.mkdir(parents=True)
    stale.write_text("old", encoding="utf-8")
    r = write_feeds(site, URL, 12)
    names = sorted(p.name for p in (site / "data" / "feeds" / "topics").glob("*"))
    assert names == ["T000001.xml", "T000002.xml"] and r["topics"] == 2           # gone topic, stale file, bad id: none
    _, tent = _entries(site / "data" / "feeds" / "topics" / "T000002.xml")
    assert [e.find(f"{A}title").text for e in tent] == [f"2026Q2: {STATUS_TH['STABLE']} / Stable"]   # only the releases it exists in


def _cfg(tmp_path, site_url):
    cfg = load_config(None)
    cfg["pipeline"].update(state_dir=str(tmp_path / "state"), output_dir=str(tmp_path / "out"))
    cfg["publish"]["site_url"] = site_url
    return cfg


def _publish_all(tmp_path, cfg, site):
    out = tmp_path / "out" / "data"
    for rel in ("2026Q1", "2026Q2"):
        if not (out / rel).exists():
            _release(out, rel, [_topic("T000001"), _topic("T000002")])
    for rel in ("2026Q1", "2026Q2"):
        r = publish_site(out / rel, site, cfg)
    return r


def test_no_feeds_without_site_url(tmp_path, capsys):
    site = tmp_path / "site"
    r = _publish_all(tmp_path, _cfg(tmp_path, None), site)
    assert r["feeds"] is None and not (site / "data" / "feeds").exists()
    assert "feeds" not in json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))
    assert "publish.site_url is not set" in capsys.readouterr().out


def test_publish_with_site_url_is_idempotent_and_keeps_feeds_out_of_the_offline_file(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "offline-template.html").write_text('<script type="application/json" id="atlas-data"></script>',
                                                encoding="utf-8")
    cfg = _cfg(tmp_path, URL)
    r = _publish_all(tmp_path, cfg, site)
    latest = json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))
    assert latest["feeds"] is True and latest["release"] == "2026Q2" and r["feeds"]["topics"] == 2
    files = {p: p.read_bytes() for p in sorted((site / "data" / "feeds").rglob("*.xml"))}
    assert len(files) == 3
    html = (site / "atlas-offline.html").read_text(encoding="utf-8")
    bundle = json.loads(re.search(r'id="atlas-data">(.*?)</script>', html, re.S).group(1))
    assert "feeds" not in bundle["latest"] and not any("feeds" in k for k in bundle["files"])
    _publish_all(tmp_path, cfg, site)                                              # same site, same files → same bytes
    assert {p: p.read_bytes() for p in sorted((site / "data" / "feeds").rglob("*.xml"))} == files
    before = (site / "data" / "latest.json").read_bytes()
    publish_site(tmp_path / "out" / "data" / "2026Q1", site, cfg)                  # older quarter: latest kept
    assert (site / "data" / "latest.json").read_bytes() == before
    assert {p: p.read_bytes() for p in sorted((site / "data" / "feeds").rglob("*.xml"))} == files


def test_topic_entries_name_the_recent_years_when_the_window_is_known(tmp_path):
    site = _site(tmp_path, [("2026Q2", [_topic("T000001")], {})])
    ov = site / "data" / "2026Q2" / "overview.json"
    ov.write_text(json.dumps({**json.loads(ov.read_text(encoding="utf-8")), "last_complete_year": 2024}), encoding="utf-8")
    write_feeds(site, URL, 12, recent_window=3)
    _, tent = _entries(site / "data" / "feeds" / "topics" / "T000001.xml")
    text = tent[0].find(f"{A}summary").text
    assert "40 articles in 2022–2024" in text and "share change +12.0% a year" in text and "STABLE" not in text
