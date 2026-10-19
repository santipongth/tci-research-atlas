"""Contract v2 export (→ validate → publish) on the 11 real ThaiJO files, as two releases."""
import hashlib
import json
import shutil

import pytest

from atlas.config import load_config
from atlas.io_utils import read_table
from atlas.pipeline import STEPS, run
from atlas.schema.contract import Manifest, model_for
from tests.conftest import FIXTURES


@pytest.fixture(scope="module")
def two_releases(tmp_path_factory):
    root = tmp_path_factory.mktemp("rel")
    for rel in ("2026Q1", "2026Q2"):
        cfg = load_config(None)
        cfg["pipeline"].update(work_dir=str(root / "work"), output_dir=str(root / "out"),
                               state_dir=str(root / "state"), release=rel)
        cfg["input"].update(path=str(FIXTURES / "thaijo_md"), workers=1)
        cfg["embedding"]["provider"] = "lite"
        cfg["clustering"]["reducer"] = "pca"
        run(cfg, STEPS)
    return root, cfg


def test_release_files_match_the_contract_and_link_back_to_thaijo(two_releases):
    root, _ = two_releases
    data = root / "out" / "data"
    assert json.loads((data / "latest.json").read_text(encoding="utf-8"))["release"] == "2026Q2"
    man = Manifest.model_validate_json((data / "2026Q2" / "manifest.json").read_text(encoding="utf-8"))
    assert man.previous_release == "2026Q1" and {f.path for f in man.files} >= {
        "overview.json", "taxonomy.json", "topics.json", "series.json", "edges.json", "keywords.json"}
    for f in man.files:
        raw = (data / "2026Q2" / f.path).read_bytes()
        assert len(raw) == f.bytes and hashlib.sha256(raw).hexdigest() == f.sha256
        model_for(f.path).model_validate_json(raw)
    topics = json.loads((data / "2026Q2" / "topics.json").read_text(encoding="utf-8"))["topics"]
    assert all(t["status"] == "LOW_DATA" and t["id"].startswith("T") for t in topics)
    assert topics[0]["lineage"]["born"] == "2026Q1" and topics[0]["lineage"]["event"] == "continue"
    assert all(t["metrics"]["low_data_reason"] in ("few_articles", "not_estimable") for t in topics)
    assert man.definition_version == 3 and man.ci_level == 0.9 and man.embedding_provider == "lite"
    assert man.labels.provider == "off" and man.labels.keywords == len(topics) and man.llm == []
    ov = json.loads((data / "2026Q2" / "overview.json").read_text(encoding="utf-8"))
    assert ov["brief"]["source"] == "template" and ov["definition_version"] == 3
    detail = json.loads((data / "2026Q2" / f"topics/{topics[0]['id']}.json").read_text(encoding="utf-8"))
    assert detail["articles"][0]["url"].startswith("https://so02.tci-thaijo.org/")
    blob = "".join(p.read_text(encoding="utf-8") for p in (data / "2026Q2").rglob("*.json"))
    docs = read_table(root / "work" / "02_docs.parquet")
    snippets = [a[:40] for a in list(docs["abstract_th"]) + list(docs["abstract_en"]) if len(a) >= 40]
    assert snippets and not any(s in blob for s in snippets)     # abstracts are never published
    tax = json.loads((data / "2026Q2" / "taxonomy.json").read_text(encoding="utf-8"))
    assert tax["source"] == "agglomerative" and all(g["color"].startswith("cat-") for g in tax["groups"])


def _copy(two_releases, tmp_path):
    root, cfg = two_releases
    dst = tmp_path / "data"
    shutil.copytree(root / "out" / "data", dst)
    return dst, cfg


def test_group_codes_never_mistake_a_fallback_group_for_an_openalex_field():
    from atlas.export_v2 import group_code
    from atlas.taxonomy import FALLBACK_GROUP_BASE

    assert group_code(33, "openalex") == "F33" and group_code(3, "agglomerative") == "G03"
    assert group_code(FALLBACK_GROUP_BASE + 5, "openalex") == "G05"


def test_no_published_group_has_an_empty_name_even_on_a_stale_taxonomy(two_releases, tmp_path, capsys):
    import pandas as pd

    from atlas.export_v2 import build_release
    from atlas.io_utils import write_table
    from atlas.taxonomy import FALLBACK_GROUP_EN, FALLBACK_GROUP_TH, TAXONOMY_COLUMNS

    root, cfg = two_releases
    for g in json.loads((root / "out" / "data" / "2026Q2" / "taxonomy.json").read_text(encoding="utf-8"))["groups"]:
        assert g["th"].strip() and g["en"].strip()
    work = tmp_path / "work"
    shutil.copytree(root / "work", work)
    info = read_table(work / "04_topic_info.parquet")
    write_table(pd.DataFrame([{"topic_id": 999, "group_id": 17, "group_en": "Computer Science", "group_th": "ก",
                               "subfield_id": "1702", "subfield_en": "AI", "vote_share": 0.9, "cross_field": False,
                               "source": "openalex"}], columns=TAXONOMY_COLUMNS), work / "10_taxonomy.parquet")
    files = build_release({**cfg, "pipeline": {**cfg["pipeline"], "work_dir": str(work)}})
    assert "WARNING" in capsys.readouterr().out                  # stale taxonomy: every topic falls back
    groups = files["taxonomy.json"].groups
    coarse = sorted({int(c) for c in info["coarse_topic"]})
    assert files["taxonomy.json"].source == "openalex"
    assert {g.id for g in groups} == {f"G{c:02d}" for c in coarse}  # never F<coarse>: not an OpenAlex field
    assert {(g.th, g.en) for g in groups} == {(FALLBACK_GROUP_TH.format(n=c), FALLBACK_GROUP_EN.format(n=c))
                                              for c in coarse}
    assert all(g.th.strip() and g.en.strip() for g in groups)
    assert {t.group for t in files["topics.json"].topics} <= {g.id for g in groups}


def test_validate_clean_release_and_diff_against_previous(two_releases):
    from atlas.validate import validate_release

    root, cfg = two_releases
    rep = validate_release(root / "out" / "data" / "2026Q2", None, cfg["validation"])
    assert rep.exit_code == 0, rep.errors + rep.warnings
    assert rep.previous_dir is not None and rep.stats["kept_ids"] == 1.0 and rep.stats["topics"] >= 1


def test_tampered_or_extra_files_are_reported(two_releases, tmp_path):
    from atlas.validate import validate_release

    data, cfg = _copy(two_releases, tmp_path)
    (data / "2026Q2" / "edges.json").write_text('{"edges": []}', encoding="utf-8")
    (data / "2026Q2" / "notes.json").write_text("{}", encoding="utf-8")
    rep = validate_release(data / "2026Q2", None, cfg["validation"])
    assert rep.exit_code == 2
    assert any("edges.json: size/sha256" in e for e in rep.errors)
    assert any("notes.json: on disk but not in the manifest" in w for w in rep.warnings)


def test_diff_flags_lost_ids_and_a_shrinking_corpus(two_releases, tmp_path):
    from atlas.validate import validate_release

    data, cfg = _copy(two_releases, tmp_path)
    prev = data / "2026Q1"
    t = json.loads((prev / "topics.json").read_text(encoding="utf-8"))
    t["topics"] += [{**t["topics"][0], "id": f"T9{i:05d}"} for i in range(3)]      # ids that vanished
    (prev / "topics.json").write_text(json.dumps(t), encoding="utf-8")
    ov = json.loads((prev / "overview.json").read_text(encoding="utf-8"))
    ov["kpis"]["articles"] = 100
    (prev / "overview.json").write_text(json.dumps(ov), encoding="utf-8")
    rep = validate_release(data / "2026Q2", prev, cfg["validation"])
    assert rep.exit_code == 2
    assert any("remain" in w for w in rep.warnings) and any("corpus shrank" in e for e in rep.errors)


def test_missing_previous_release_only_warns(two_releases, tmp_path):
    from atlas.validate import validate_release

    root, cfg = two_releases
    rep = validate_release(root / "out" / "data" / "2026Q2", tmp_path / "no-such-release", cfg["validation"])
    assert rep.exit_code == 1 and any("diff skipped" in w for w in rep.warnings)


def test_cli_validate_exit_codes(two_releases, tmp_path):
    from typer.testing import CliRunner

    from atlas.cli import app

    root, _ = two_releases
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(f"pipeline:\n  output_dir: '{(root / 'out').as_posix()}'\n  release: 2026Q2\n",
                        encoding="utf-8")
    res = CliRunner().invoke(app, ["validate", "--config", str(cfg_file)])
    assert res.exit_code == 0 and "atlas validate: OK" in res.stdout
    res = CliRunner().invoke(app, ["validate", "--dir", str(tmp_path / "empty")])
    assert res.exit_code == 2 and "manifest.json is missing" in res.stdout


def test_llm_fallbacks_are_reported(two_releases, tmp_path):
    from atlas.validate import validate_release

    data, cfg = _copy(two_releases, tmp_path)
    path = data / "2026Q2" / "manifest.json"
    m = json.loads(path.read_text(encoding="utf-8"))
    m["labels"] = {"provider": "llm", "llm": 2, "keywords": 1, "overrides": 0}
    m["llm"] = [{"task": "narrative", "model": "m", "items": 4, "from_cache": 0, "generated": 3, "repaired": 0,
                 "fallback": 1, "cost_usd": 0.01}]
    path.write_text(json.dumps(m), encoding="utf-8")              # the manifest does not hash itself
    rep = validate_release(data / "2026Q2", None, cfg["validation"])
    assert rep.exit_code == 1
    assert any("fell back to keywords" in w for w in rep.warnings)
    assert any("narrative: 1 of 4" in w for w in rep.warnings)


TEMPLATE = ('<!doctype html><html><head><title>Atlas</title></head><body><div id="root"></div>'
            '<script type="application/json" id="atlas-data">null</script><script src="assets/app.js"></script>'
            '</body></html>')


def test_publish_to_the_site_writes_data_latest_and_the_offline_html(two_releases, tmp_path):
    import re

    from atlas.publish import publish

    root, cfg = two_releases
    site = tmp_path / "site"
    site.mkdir()
    (site / "offline-template.html").write_text(TEMPLATE, encoding="utf-8")
    for rel in ("2026Q1", "2026Q2"):                                   # two quarters, published in order
        r = publish({**cfg, "pipeline": {**cfg["pipeline"], "release": rel}}, site=site)
    latest = json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))
    assert latest["release"] == "2026Q2" and (site / "data" / latest["path"]).exists()
    assert (site / "data" / "2026Q1" / "manifest.json").exists()      # older quarters stay for comparison
    html = (site / "atlas-offline.html").read_text(encoding="utf-8")
    bundle = json.loads(re.search(r'id="atlas-data">(.*?)</script>', html, re.S).group(1))
    assert bundle["latest"]["release"] == "2026Q2" and "topics.json" in bundle["files"]
    assert any(k.startswith("topics/T") for k in bundle["files"]) and '<script src="assets/app.js">' in html
    assert r["offline_html"].endswith("atlas-offline.html") and "tarball" not in r


def test_offline_injection_escapes_script_ends_and_needs_the_data_tag():
    from atlas.publish import inject_offline

    html = inject_offline(TEMPLATE, {"x": "</script><b>"})
    assert html.count("</script>") == 2 and "<\\/script><b>" in html
    with pytest.raises(ValueError, match="atlas-data"):
        inject_offline("<html></html>", {})


def test_site_without_a_template_still_gets_the_data(two_releases, tmp_path, capsys):
    from atlas.publish import publish

    root, cfg = two_releases
    r = publish({**cfg, "pipeline": {**cfg["pipeline"], "release": "2026Q2"}}, site=tmp_path / "bare")
    assert r["offline_html"] is None and (tmp_path / "bare" / "data" / "latest.json").exists()
    assert "offline-template.html not found" in capsys.readouterr().out


def test_package_is_reproducible_and_broken_releases_are_refused(two_releases, tmp_path):
    import tarfile

    from atlas.publish import PublishRefused, package_release, publish

    root, cfg = two_releases
    rel = root / "out" / "data" / "2026Q2"
    a = package_release(rel, tmp_path / "a")
    b = package_release(rel, tmp_path / "b")
    assert a[1].read_text().split()[0] == b[1].read_text().split()[0]
    with tarfile.open(a[0]) as tar:
        names = tar.getnames()
    assert "2026Q2/manifest.json" in names and all(n.startswith("2026Q2/") for n in names)
    data, cfg2 = _copy(two_releases, tmp_path)
    (data / "2026Q2" / "topics.json").write_text("{}", encoding="utf-8")
    cfg2 = {**cfg2, "pipeline": {**cfg2["pipeline"], "output_dir": str(tmp_path), "release": "2026Q2"}}
    with pytest.raises(PublishRefused):
        publish(cfg2, site=tmp_path / "site")
    assert not (tmp_path / "site").exists()                         # nothing reaches the site when refused


def test_cli_publish_needs_a_target_and_never_runs_gh(two_releases, tmp_path, monkeypatch):
    import subprocess

    from typer.testing import CliRunner

    from atlas.cli import app

    def no_subprocess(*a, **k):
        raise AssertionError("publish must not start processes")

    monkeypatch.setattr(subprocess, "run", no_subprocess)
    monkeypatch.setattr(subprocess, "Popen", no_subprocess)
    root, _ = two_releases
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(f"pipeline:\n  output_dir: '{(root / 'out').as_posix()}'\n  release: 2026Q2\n",
                        encoding="utf-8")
    assert CliRunner().invoke(app, ["publish", "--config", str(cfg_file)]).exit_code == 2
    res = CliRunner().invoke(app, ["publish", "--config", str(cfg_file), "--tarball", "--site", str(tmp_path / "s")])
    assert res.exit_code == 0 and "gh release create data-2026Q2" in res.stdout and "latest.json" in res.stdout
    notes = (root / "out" / "releases" / "atlas-data-2026Q2.notes.md").read_text(encoding="utf-8")
    assert notes.startswith("# TCI Research Atlas — data 2026Q2") and "LOW_DATA" in notes


def test_offline_payload_cannot_enter_the_escaped_script_state():
    import re

    from atlas.publish import inject_offline

    html = inject_offline(TEMPLATE, {"title": "a <!--<script> b </script> c"})
    slot = re.search(r'id="atlas-data">(.*?)</script>', html, re.S).group(1)
    assert "<!--" not in slot and "</" not in slot
    assert json.loads(slot) == {"title": "a <!--<script> b </script> c"}


def test_missing_previous_release_named_by_the_manifest_warns(two_releases, tmp_path):
    from atlas.validate import validate_release

    data, cfg = _copy(two_releases, tmp_path)
    shutil.rmtree(data / "2026Q1")
    rep = validate_release(data / "2026Q2", None, cfg["validation"])
    assert rep.exit_code == 1 and any("2026Q1 not found" in w and "diff skipped" in w for w in rep.warnings)


def test_release_names_are_checked_and_must_match_the_manifest(two_releases, tmp_path):
    from atlas.publish import PublishRefused, publish
    from atlas.validate import validate_release

    data, cfg = _copy(two_releases, tmp_path)
    with pytest.raises(PublishRefused, match="invalid release name"):
        publish(cfg, release="../x", site=tmp_path / "site")
    shutil.copytree(data / "2026Q2", data / "2026Q9")                 # folder name != manifest.release
    rep = validate_release(data / "2026Q9", None, cfg["validation"])
    assert rep.exit_code == 2 and any("does not match the folder name" in e for e in rep.errors)
    cfg2 = {**cfg, "pipeline": {**cfg["pipeline"], "output_dir": str(tmp_path)}}
    with pytest.raises(PublishRefused):
        publish(cfg2, release="2026Q9", site=tmp_path / "site")


def test_diff_skips_malformed_previous_topic_entries(two_releases, tmp_path):
    from atlas.validate import validate_release

    data, cfg = _copy(two_releases, tmp_path)
    prev = data / "2026Q1"
    t = json.loads((prev / "topics.json").read_text(encoding="utf-8"))
    del t["topics"][0]["size"]
    t["topics"].append({"id": "T999999", "size": 5})                 # no status
    (prev / "topics.json").write_text(json.dumps(t), encoding="utf-8")
    rep = validate_release(data / "2026Q2", prev, cfg["validation"])
    assert any("lack id/size/status" in w for w in rep.warnings)
