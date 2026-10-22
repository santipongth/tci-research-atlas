"""Atom 1.0 feeds written by `atlas publish --site` when publish.site_url is set (P4, R11).

  <site>/data/feeds/releases.xml         one entry per release on the site, newest first (≤ publish.feed_max_entries):
                                         title = release, summary = overview headline (TH, EN) + what changed
                                         (new / gone / status changes from diff.json when present), link #/changes
  <site>/data/feeds/topics/<id>.xml      one feed per topic of the newest release on the site; entries = the releases
                                         (newest first, same cap) where the topic exists: status, articles in the
                                         recent window, share growth; link #/topics/<id>

Built only from the release folders already on the site (data/<release>/manifest.json, overview.json, diff.json,
topics.json), so a re-run gives the same bytes. The XML is written by hand (xml.sax.saxutils.escape) — no
timestamps of our own: a feed's <updated> is the newest release's manifest generated_at, an entry's is its release's.
Topic feeds of topics no longer in the newest release are removed. The feeds point at site_url (absolute links), so
the single-file offline edition does not carry them.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from atlas.schema.contract import TOPIC_ID
from atlas.state import _checked

ATOM_NS = "http://www.w3.org/2005/Atom"
FEEDS_DIR = "feeds"
_TOPIC_ID = re.compile(TOPIC_ID)
_CONTROL = re.compile("[" + "".join(map(chr, [*range(0x00, 0x09), 0x0B, 0x0C, *range(0x0E, 0x20), 0xFFFE, 0xFFFF])) + "]")   # not allowed in XML 1.0


def _text(s) -> str:
    return escape(_CONTROL.sub("", str(s)))


def _attr(s) -> str:
    return escape(_CONTROL.sub("", str(s)), {'"': "&quot;"})


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def site_releases(site: str | Path) -> list[str]:
    """Release folders on the site (with a manifest), newest first."""
    out = []
    for p in (Path(site) / "data").glob("*"):
        try:
            _checked(p.name)
        except ValueError:
            continue
        if (p / "manifest.json").is_file():
            out.append(p.name)
    return sorted(out, reverse=True)


def _pct(v) -> str:
    return "n/a" if v is None else f"{float(v) * 100:+.1f}%"


def _feed(feed_id: str, title: str, updated: str, alternate: str, entries: list[dict]) -> str:
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             f'<feed xmlns="{ATOM_NS}" xml:lang="th">',
             f"  <id>{_text(feed_id)}</id>",
             f"  <title>{_text(title)}</title>",
             f"  <updated>{_text(updated)}</updated>",
             f'  <link rel="self" type="application/atom+xml" href="{_attr(feed_id)}"/>',
             f'  <link rel="alternate" type="text/html" href="{_attr(alternate)}"/>',
             "  <author><name>TCI Research Atlas</name></author>"]
    for e in entries:
        lines += ["  <entry>",
                  f"    <id>{_text(e['id'])}</id>",
                  f"    <title>{_text(e['title'])}</title>",
                  f"    <updated>{_text(e['updated'])}</updated>",
                  f'    <link rel="alternate" type="text/html" href="{_attr(e["link"])}"/>',
                  f"    <summary>{_text(e['summary'])}</summary>",
                  "  </entry>"]
    lines.append("</feed>")
    return "\n".join(lines) + "\n"


def _release_summary(folder: Path) -> str:
    ov = _read(folder / "overview.json") or {}
    brief, k = ov.get("brief") or {}, ov.get("kpis") or {}
    parts = [p for p in (brief.get("headline_th"), brief.get("headline_en")) if p]
    if not parts and k:
        parts.append(f"{int(k.get('articles', 0)):,} articles · {int(k.get('topics', 0)):,} topics")
    diff = _read(folder / "diff.json")
    if isinstance(diff, dict):
        parts.append(f"vs {diff.get('previous_release', '?')}: {len(diff.get('new_topics') or [])} new topics · "
                     f"{len(diff.get('retired') or [])} gone · {len(diff.get('status_changes') or [])} status changes")
    return "\n".join(parts) or folder.name


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def write_feeds(site: str | Path, site_url: str, max_entries: int = 12) -> dict:
    """Write data/feeds/ under the site from the releases on it → {"releases": path, "topics": n, "entries": n}."""
    site = Path(site)
    base = site_url.strip()
    base = base if base.endswith("/") else base + "/"
    data = site / "data"
    releases = site_releases(site)
    if not releases:
        raise ValueError(f"no release on the site ({data}) — nothing to put in a feed")
    shown = releases[:max_entries]
    stamp = {r: str((_read(data / r / "manifest.json") or {}).get("generated_at", "")) for r in releases}
    feeds = data / FEEDS_DIR
    entries = [{"id": f"{base}data/{r}/manifest.json", "title": r, "updated": stamp[r],
                "link": f"{base}#/changes", "summary": _release_summary(data / r)} for r in shown]
    _write(feeds / "releases.xml", _feed(f"{base}data/{FEEDS_DIR}/releases.xml", "TCI Research Atlas — releases",
                                         stamp[releases[0]], f"{base}#/changes", entries))

    topics_by_release = {}
    for r in shown:
        tf = _read(data / r / "topics.json")
        rows = tf.get("topics") if isinstance(tf, dict) else None
        topics_by_release[r] = {t["id"]: t for t in rows or [] if isinstance(t, dict) and _TOPIC_ID.match(str(t.get("id", "")))}
    newest = topics_by_release.get(releases[0], {})
    written = set()
    for code in sorted(newest):
        t = newest[code]
        ent = []
        for r in shown:
            x = topics_by_release[r].get(code)
            if x is None:
                continue
            m = x.get("metrics") or {}
            ent.append({"id": f"{base}data/{r}/topics/{code}.json", "title": f"{r}: {x.get('status', '?')}",
                        "updated": stamp[r], "link": f"{base}#/topics/{code}",
                        "summary": f"{x.get('th', '')} / {x.get('en', '')}\n{x.get('status', '?')} · "
                                   f"{int(m.get('count_recent') or 0):,} articles in the recent window · "
                                   f"share growth {_pct(m.get('share_growth'))}"})
        name = f"{code}.xml"
        _write(feeds / "topics" / name, _feed(f"{base}data/{FEEDS_DIR}/topics/{name}",
                                              f"TCI Research Atlas — {t.get('th', '')} / {t.get('en', '')}",
                                              stamp[releases[0]], f"{base}#/topics/{code}", ent))
        written.add(name)
    for stale in (feeds / "topics").glob("*.xml"):
        if stale.name not in written:
            stale.unlink()
    print(f"[publish] Atom feeds: {feeds / 'releases.xml'} ({len(entries)} releases) + {len(written):,} topic feeds")
    return {"releases": str(feeds / "releases.xml"), "topics": len(written), "entries": len(entries)}
