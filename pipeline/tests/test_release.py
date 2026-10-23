"""Contract v2 export (→ validate → publish) on the 11 real ThaiJO files, as two releases."""
import hashlib
import json
import shutil
from datetime import date, datetime
from pathlib import Path

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


def test_institutions_are_published_with_their_written_names(two_releases):
    root, _ = two_releases
    rel = root / "out" / "data" / "2026Q2"
    inst = {i["key"]: i["count"] for p in (rel / "topics").glob("*.json")
            for i in json.loads(p.read_text(encoding="utf-8"))["institutions"]}
    # real fixture affiliations: the karan / tone marks and the case survive (org_key folds them for counting only)
    assert "มหาวิทยาลัยเกษตรศาสตร์" in inst and "มหาวิทยาลัยฮาร์วาร์ด" in inst and "Naresuan University" in inst
    assert inst["มหาวิทยาลัยนเรศวร"] == 5
    assert not {"มหาวิทยาลัยเกษตรศาสตร", "naresuanuniversity", "มหาวิทยาลัยฮารวารด"} & set(inst)
    ov = json.loads((rel / "overview.json").read_text(encoding="utf-8"))
    assert ov["kpis"]["institutions"] == 8                          # counting is still by org_key


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


# ---- release ↔ work_dir guard (P1a final review): a step after `cluster` never writes another release
def _workspace(two_releases, tmp_path, release):
    """A private copy of work/state/out of the fixture (work_dir clustered for 2026Q2) with pipeline.release set."""
    root, cfg = two_releases
    for d in ("work", "state", "out"):
        shutil.copytree(root / d, tmp_path / d)
    pipe = {**cfg["pipeline"], "work_dir": str(tmp_path / "work"), "state_dir": str(tmp_path / "state"),
            "output_dir": str(tmp_path / "out"), "release": release}
    return {**cfg, "pipeline": pipe}


def _digest(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


@pytest.mark.parametrize("release", ["2027Q1", "2026Q1"])          # phantom release / overwrite an older one
@pytest.mark.parametrize("step", ["label", "narrate", "layout", "export"])
def test_steps_after_cluster_refuse_another_release(two_releases, tmp_path, release, step):
    from atlas.state import ReleaseMismatch

    cfg = _workspace(two_releases, tmp_path, release)
    before_out, before_state = _digest(tmp_path / "out"), _digest(tmp_path / "state")
    with pytest.raises(ReleaseMismatch, match=f"work_dir was clustered for 2026Q2 but pipeline.release is {release}"):
        run(cfg, [step])
    assert _digest(tmp_path / "out") == before_out and _digest(tmp_path / "state") == before_state
    assert not (tmp_path / "out" / "data" / "2027Q1").exists() and not (tmp_path / "state" / "releases" / "2027Q1").exists()


def test_cli_run_names_the_mismatch_and_exits_2(two_releases, tmp_path):
    from typer.testing import CliRunner

    from atlas.cli import app

    cfg = _workspace(two_releases, tmp_path, "2027Q1")
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text("pipeline:\n" + "".join(f"  {k}: '{Path(cfg['pipeline'][k]).as_posix()}'\n"
                                                 for k in ("work_dir", "state_dir", "output_dir"))
                        + "  release: 2027Q1\n", encoding="utf-8")
    res = CliRunner().invoke(app, ["run", "-c", str(cfg_file), "-s", "export"])
    assert res.exit_code == 2 and "work_dir was clustered for 2026Q2 but pipeline.release is 2027Q1" in res.output
    assert not (tmp_path / "out" / "data" / "2027Q1").exists()


def test_null_release_continued_next_quarter_publishes_the_clustered_release(two_releases, tmp_path, monkeypatch):
    import atlas.state as state
    from atlas.publish import publish
    from atlas.validate import validate_release

    cfg = _workspace(two_releases, tmp_path, None)
    monkeypatch.setattr(state, "today", lambda: date(2027, 1, 5))       # days later, in the next quarter
    run(cfg, ["label", "narrate", "export"])
    data = tmp_path / "out" / "data"
    assert sorted(p.name for p in data.iterdir() if p.is_dir()) == ["2026Q1", "2026Q2"]
    man = json.loads((data / "2026Q2" / "manifest.json").read_text(encoding="utf-8"))
    assert man["release"] == "2026Q2" and man["previous_release"] == "2026Q1"
    assert json.loads((data / "latest.json").read_text(encoding="utf-8"))["release"] == "2026Q2"
    assert validate_release(data / "2026Q2", None, cfg["validation"]).exit_code in (0, 1)
    r = publish(cfg, site=tmp_path / "site", allow_warnings=True)          # null → the work_dir's release
    assert r["release"] == "2026Q2" and (tmp_path / "site" / "data" / "2026Q2" / "manifest.json").exists()
    assert (tmp_path / "state" / "releases" / "index.json").read_text(encoding="utf-8") == '["2026Q1", "2026Q2"]'


def test_cli_validate_defaults_to_the_work_dir_release(two_releases, tmp_path, monkeypatch):
    from typer.testing import CliRunner

    import atlas.state as state
    from atlas.cli import app

    cfg = _workspace(two_releases, tmp_path, None)
    monkeypatch.setattr(state, "today", lambda: date(2027, 1, 5))
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text("pipeline:\n" + "".join(f"  {k}: '{Path(cfg['pipeline'][k]).as_posix()}'\n"
                                                 for k in ("work_dir", "state_dir", "output_dir")), encoding="utf-8")
    res = CliRunner().invoke(app, ["validate", "-c", str(cfg_file)])
    assert res.exit_code in (0, 1) and "2026Q2" in res.output and "2027Q1" not in res.output


def test_two_exports_of_the_same_release_are_byte_identical(two_releases, tmp_path):
    cfg = _workspace(two_releases, tmp_path, "2026Q2")
    run(cfg, ["export"])
    first = _digest(tmp_path / "out")
    run(cfg, ["export"])
    assert _digest(tmp_path / "out") == first
    snap = json.loads((tmp_path / "work" / "04_topics_meta.json").read_text(encoding="utf-8"))["snapshot_at"]
    man = json.loads((tmp_path / "out" / "data" / "2026Q2" / "manifest.json").read_text(encoding="utf-8"))
    assert datetime.fromisoformat(man["generated_at"]) == datetime.fromisoformat(snap)   # the recorded snapshot


def test_publishing_an_older_release_keeps_the_site_latest(two_releases, tmp_path, capsys):
    from atlas.publish import publish

    root, cfg = two_releases
    site = tmp_path / "site"
    for rel in ("2026Q1", "2026Q2", "2026Q1"):                        # re-publish an older quarter last
        publish({**cfg, "pipeline": {**cfg["pipeline"], "release": rel}}, site=site)
    assert json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))["release"] == "2026Q2"
    assert "latest.json still points at 2026Q2" in capsys.readouterr().out
    publish({**cfg, "pipeline": {**cfg["pipeline"], "release": "2026Q1"}}, site=site, set_latest=True)
    assert json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))["release"] == "2026Q1"


def test_ingest_errors_are_null_when_not_recorded(two_releases, tmp_path):
    cfg = _workspace(two_releases, tmp_path, "2026Q2")
    man = tmp_path / "out" / "data" / "2026Q2" / "manifest.json"
    run(cfg, ["export"])
    assert json.loads(man.read_text(encoding="utf-8"))["ingest_errors"] == 0           # recorded: no file failed
    (tmp_path / "work" / "01_ingest_errors.parquet").unlink()                         # a work_dir from before P0 F11
    run(cfg, ["export"])
    assert json.loads(man.read_text(encoding="utf-8"))["ingest_errors"] is None        # unknown, never a claimed 0
    Manifest.model_validate_json(man.read_text(encoding="utf-8"))


def test_manifest_llm_cost_is_the_release_total_plus_this_run(two_releases, tmp_path):
    from atlas.export_v2 import _llm_stats

    cfg = _workspace(two_releases, tmp_path, "2026Q2")
    work, cache = tmp_path / "work", tmp_path / "state" / "llm_cache"
    cache.mkdir(parents=True)
    (cache / "label.jsonl").write_text("\n".join(json.dumps(r) for r in [
        {"key": "a", "task": "label", "release": "2026Q1", "cost_usd": 0.5, "output": {}},
        {"key": "b", "task": "label", "release": "2026Q2", "cost_usd": 0.01, "output": None},   # paid, then fallback
        {"key": "c", "task": "label", "release": "2026Q2", "cost_usd": 0.02, "output": {}}]) + "\n", encoding="utf-8")
    (work / "05_labels_meta.json").write_text(json.dumps({"provider": "llm", "model_id": "m", "topics": 3, "reused": 2,
                                                          "generated": 1, "cost_usd": 0.02}), encoding="utf-8")
    (st,) = _llm_stats(cfg, work, {}, "2026Q2")
    assert (st.task, st.cost_usd, st.this_run_cost_usd) == ("label", 0.03, 0.02)
    assert st.items == 1                                           # 2 of 3 topics kept last release's name


def test_group_colours_follow_the_group_id_not_its_size_rank(two_releases):
    import re

    from atlas.export_v2 import group_color, group_colors

    common = ["F33", "F14", "F12", "F27", "F11", "F32", "F20", "F22", "F17", "F29", "F23", "F36"]
    assert len({group_color(c) for c in common}) == 12          # the 12 most common TCI fields never share a colour
    assert all(re.fullmatch(r"cat-(0[1-9]|1[0-2])", group_color(f"F{f}")) for f in range(11, 37))
    assert [group_color(f"G{n:02d}") for n in range(13)] == [f"cat-{n % 12 + 1:02d}" for n in range(13)]
    assert group_color("F33") == "cat-01" and group_color("F99") == group_color("F99")   # unknown field: stable too
    root, _ = two_releases
    tax = json.loads((root / "out" / "data" / "2026Q2" / "taxonomy.json").read_text(encoding="utf-8"))
    assert all(g["color"] == group_colors([x["id"] for x in tax["groups"]])[g["id"]] for g in tax["groups"])
    # one release's groups never share a colour (≤ 12): a collision moves the higher id to the next free token
    assert group_colors(["F23", "F30", "F14"]) == {"F23": "cat-11", "F30": "cat-12", "F14": "cat-02"}
    assert group_colors(["F30", "F14"]) == {"F30": "cat-11", "F14": "cat-02"}            # no collision: as preferred
    assert len(set(group_colors([f"F{f}" for f in range(11, 23)]).values())) == 12


def test_publish_restores_earlier_releases_the_site_lacks(two_releases, tmp_path, capsys):
    from atlas.publish import publish

    root, cfg = two_releases
    site = tmp_path / "site"
    (site / "data").mkdir(parents=True)                               # `npm run build` emptied dist/data
    r = publish({**cfg, "pipeline": {**cfg["pipeline"], "release": "2026Q2"}}, site=site)
    assert r["restored"] == ["2026Q1"] and (site / "data" / "2026Q1" / "manifest.json").exists()
    assert _digest(site / "data" / "2026Q1") == _digest(root / "out" / "data" / "2026Q1")
    assert json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))["release"] == "2026Q2"
    # a release folder already on the site is never replaced by the restore
    (site / "data" / "2026Q1" / "topics.json").write_text('{"edited": true}', encoding="utf-8")
    r = publish({**cfg, "pipeline": {**cfg["pipeline"], "release": "2026Q2"}}, site=site)
    assert r["restored"] == [] and (site / "data" / "2026Q1" / "topics.json").read_text(encoding="utf-8") == '{"edited": true}'
    # the previous release is nowhere (not in output/data, not on the site): a warning, the publish goes on
    data, cfg2 = _copy(two_releases, tmp_path)
    shutil.rmtree(data / "2026Q1")
    capsys.readouterr()
    r = publish({**cfg2, "pipeline": {**cfg2["pipeline"], "output_dir": str(tmp_path), "release": "2026Q2"}},
                site=tmp_path / "site2", allow_warnings=True)
    assert r["restored"] == [] and "previous release 2026Q1 is not in" in capsys.readouterr().out
    assert (tmp_path / "site2" / "data" / "2026Q2" / "manifest.json").exists()


# ---------------------------------------------------------------- P2: editors' modules (contract 2.1)
def test_editor_modules_are_published_and_valid(two_releases):
    root, _ = two_releases
    rel = root / "out" / "data" / "2026Q2"
    man = Manifest.model_validate_json((rel / "manifest.json").read_text(encoding="utf-8"))
    assert man.schema_version == "2.3.0"
    assert {"journals", "journal_detail", "methods", "match", "diff"} <= set(man.modules)
    paths = {f.path for f in man.files}
    assert {"journals.json", "journals/so02.BECJournal.json", "methods.json", "match.json", "diff.json"} <= paths
    for p in paths:
        model_for(p).model_validate_json((rel / p).read_bytes())
    jf = json.loads((rel / "journals.json").read_text(encoding="utf-8"))
    j = jf["journals"][0]
    assert j["id"] == "so02.BECJournal" and j["path"] == "BECJournal" and j["name_th"] == ""
    assert j["low_data"] is True and j["inhouse_share"] is None      # 11 articles < journals.min_articles
    topics = json.loads((rel / "topics.json").read_text(encoding="utf-8"))["topics"]
    detail = json.loads((rel / f"topics/{topics[0]['id']}.json").read_text(encoding="utf-8"))
    assert detail["journals"][0]["id"] == "so02.BECJournal" and detail["journals"][0]["key"] == "BECJournal"
    diff = json.loads((rel / "diff.json").read_text(encoding="utf-8"))
    assert diff["previous_release"] == "2026Q1" and diff["previous_source"] == "state"
    assert "diff" not in json.loads((root / "out" / "data" / "2026Q1" / "manifest.json").read_text(
        encoding="utf-8"))["modules"]                                 # the first release has nothing to compare
    assert (root / "state" / "releases" / "2026Q2" / "snapshot.json").exists()


def test_registry_names_journals_in_the_release(two_releases, tmp_path):
    cfg = _workspace(two_releases, tmp_path, "2026Q2")
    reg = tmp_path / "journals.csv"
    reg.write_text("journal_key,name_th,tci_tier,publisher_org\nBECJournal,วารสารทดสอบ,2,มหาวิทยาลัยนเรศวร\n",
                   encoding="utf-8")
    cfg = {**cfg, "journals": {**cfg["journals"], "registry_path": str(reg)}}   # never edit the shared fixture
    run(cfg, ["journals", "export"])
    rel = Path(cfg["pipeline"]["output_dir"]) / "data" / "2026Q2"
    j = json.loads((rel / "journals.json").read_text(encoding="utf-8"))["journals"][0]
    assert j["name_th"] == "วารสารทดสอบ" and j["tci_tier"] == 2 and j["owner_source"] == "registry"
    topics = json.loads((rel / "topics.json").read_text(encoding="utf-8"))["topics"]
    detail = json.loads((rel / f"topics/{topics[0]['id']}.json").read_text(encoding="utf-8"))
    assert detail["journals"][0]["key"] == "วารสารทดสอบ"


def _rewrite(rel_dir, path, obj):
    """Replace one published file and keep the manifest's size/sha256 in step (a coherent tampering)."""
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    (rel_dir / path).write_bytes(data)
    man = json.loads((rel_dir / "manifest.json").read_text(encoding="utf-8"))
    for f in man["files"]:
        if f["path"] == path:
            f.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    (rel_dir / "manifest.json").write_text(json.dumps(man), encoding="utf-8")


def test_validate_checks_the_editor_modules(two_releases, tmp_path):
    from atlas.validate import validate_release

    data, cfg = _copy(two_releases, tmp_path)
    rel = data / "2026Q2"
    assert validate_release(rel, None, cfg["validation"]).exit_code == 0
    detail = json.loads((rel / "journals/so02.BECJournal.json").read_text(encoding="utf-8"))
    _rewrite(rel, "journals/so02.BECJournal.json", {**detail, "peers": [{"id": "so09.Ghost", "similarity": 0.5}]})
    diff = json.loads((rel / "diff.json").read_text(encoding="utf-8"))
    _rewrite(rel, "diff.json", {**diff, "movers": [{"topic": "T999999", "share_previous": 0.1, "share_current": 0.2}]})
    rep = validate_release(rel, None, {**cfg["validation"], "max_file_bytes": 100})
    assert rep.exit_code == 2
    assert any("peers not in journals.json: ['so09.Ghost']" in e for e in rep.errors)
    assert any("diff.json: topics not in topics.json: ['T999999']" in e for e in rep.errors)
    assert any("validation.max_file_bytes" in w for w in rep.warnings)


def test_offline_edition_leaves_out_the_match_index(two_releases, tmp_path):
    import re

    from atlas.publish import publish

    root, cfg = two_releases
    site = tmp_path / "site"
    site.mkdir()
    (site / "offline-template.html").write_text(TEMPLATE, encoding="utf-8")
    publish({**cfg, "pipeline": {**cfg["pipeline"], "release": "2026Q2"}}, site=site)
    html = (site / "atlas-offline.html").read_text(encoding="utf-8")
    files = json.loads(re.search(r'id="atlas-data">(.*?)</script>', html, re.S).group(1))["files"]
    assert "match.json" not in files and "journals.json" in files and "diff.json" in files
    assert (site / "data" / "2026Q2" / "match.json").exists()          # the web edition keeps it
    old_cfg = {**cfg, "pipeline": {**cfg["pipeline"], "release": "2026Q2"},
               "export": {**cfg["export"], "offline_exclude": ["match.json"]}}     # a config.yaml from before P4
    publish(old_cfg, site=site)
    html = (site / "atlas-offline.html").read_text(encoding="utf-8")
    files = json.loads(re.search(r'id="atlas-data">(.*?)</script>', html, re.S).group(1))["files"]
    assert not [f for f in files if f.startswith("search/") or f == "galaxy.json"] and "match.json" not in files
    assert (site / "data" / "2026Q2" / "search" / "meta.json").exists()


def test_validate_checks_the_merge_links_of_the_diff(two_releases, tmp_path):
    from atlas.validate import validate_release

    data, cfg = _copy(two_releases, tmp_path)
    rel = data / "2026Q2"
    diff = json.loads((rel / "diff.json").read_text(encoding="utf-8"))
    _rewrite(rel, "diff.json", {**diff, "retired": [{"topic": "T999990", "merged_into": "T999991"}],
                                "restructured": [{"topic": "T999992", "event": "merge", "parents": []}]})
    rep = validate_release(rel, None, cfg["validation"])
    assert any("diff.json: topics not in topics.json: ['T999991', 'T999992']" in e for e in rep.errors)


# ---------------------------------------------------------------- P3: executives' modules (contract 2.2)
def test_executive_modules_are_published_valid_and_name_no_person(two_releases):
    from atlas.validate import validate_release

    root, cfg = two_releases
    rel = root / "out" / "data" / "2026Q2"
    man = Manifest.model_validate_json((rel / "manifest.json").read_text(encoding="utf-8"))
    assert {"institutions", "institution_detail", "regions", "sdg", "gaps"} <= set(man.modules)
    assert "global" not in man.modules and man.skipped_modules.get("global")       # offline, no OpenAlex map
    assert validate_release(rel, None, cfg["validation"]).errors == []
    people = {n for n in read_table(root / "work" / "01_authors.parquet")["name"].fillna("").astype(str) if len(n) >= 6}
    blob = "".join(p.read_text(encoding="utf-8") for p in rel.rglob("*.json"))
    assert people and not any(n in blob for n in people)                         # no person, anywhere
    inst = json.loads((rel / "institutions.json").read_text(encoding="utf-8"))
    assert all(i["articles"] >= cfg["institutions"]["min_articles"] for i in inst["institutions"])
    sdg = json.loads((rel / "sdg.json").read_text(encoding="utf-8"))
    assert sdg["method"] == "lexical" and len([g for g in sdg["goals"] if g["framework"] == "sdg"]) == 17


def test_researcher_modules_are_valid_and_carry_no_person_and_no_abstract(two_releases):
    root, _ = two_releases
    rel = root / "out" / "data" / "2026Q2"
    man = Manifest.model_validate_json((rel / "manifest.json").read_text(encoding="utf-8"))
    p4 = [f.path for f in man.files if f.path in ("references.json", "galaxy.json", "kwtrends.json")
          or f.path.startswith("search/")]
    assert {"search/meta.json", "search/vocab.json", "kwtrends.json"} <= set(p4)
    assert any(p.startswith("search/idx-") for p in p4) and any(p.startswith("search/docs-") for p in p4)
    for p in p4:
        model_for(p).model_validate_json((rel / p).read_bytes())
    blob = "".join((rel / p).read_text(encoding="utf-8") for p in p4)
    blob += "".join(json.dumps(json.loads(t.read_text(encoding="utf-8")).get("glossary") or [], ensure_ascii=False)
                    for t in (rel / "topics").glob("*.json"))
    people = {n for n in read_table(root / "work" / "01_authors.parquet")["name"].fillna("").astype(str) if len(n) >= 6}
    assert people and not any(n in blob for n in people)                         # no author name in any P4 file
    docs = read_table(root / "work" / "02_docs.parquet")
    snippets = [a[:40] for a in list(docs["abstract_th"].fillna("").astype(str)) +
                list(docs["abstract_en"].fillna("").astype(str)) if len(a) >= 40]
    assert snippets and not any(s in blob for s in snippets)                     # no abstract text either


def test_publish_with_a_site_url_writes_atom_feeds_for_the_real_release(two_releases, tmp_path):
    import xml.etree.ElementTree as ET

    from atlas.publish import publish

    root, cfg = two_releases
    site = tmp_path / "site"
    pub = {**cfg["publish"], "site_url": "https://example.github.io/atlas/"}
    for rel in ("2026Q1", "2026Q2"):
        publish({**cfg, "pipeline": {**cfg["pipeline"], "release": rel}, "publish": pub}, site=site)
    assert json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))["feeds"] is True
    entries = ET.parse(site / "data" / "feeds" / "releases.xml").getroot().findall("{http://www.w3.org/2005/Atom}entry")
    assert [e.find("{http://www.w3.org/2005/Atom}title").text for e in entries] == ["2026Q2", "2026Q1"]
    topics = json.loads((site / "data" / "2026Q2" / "topics.json").read_text(encoding="utf-8"))["topics"]
    feeds = sorted((site / "data" / "feeds" / "topics").glob("*.xml"))
    assert [p.stem for p in feeds] == sorted(t["id"] for t in topics)
    for p in feeds:
        ET.parse(p)


# ---------------------------------------------------------------- web refresh: plain public sentences
def test_published_template_sentences_are_plain_language(two_releases, tmp_path):
    """Every sentence the pipeline writes for the public (brief, policy notes, topic narratives, method notes, feed
    summaries) avoids the banned jargon and never puts a status code where the status name belongs."""
    import xml.etree.ElementTree as ET

    from atlas.narrative import jargon_in
    from atlas.publish import publish

    root, cfg = two_releases
    rel = root / "out" / "data" / "2026Q2"
    ov = json.loads((rel / "overview.json").read_text(encoding="utf-8"))
    texts = [ov["brief"]["headline_th"], ov["brief"]["headline_en"], *ov["brief"]["bullets_th"],
             *ov["brief"]["bullets_en"]]
    texts += [*(ov.get("executive") or {}).get("bullets_th", []), *(ov.get("executive") or {}).get("bullets_en", [])]
    for p in (rel / "topics").glob("*.json"):
        n = json.loads(p.read_text(encoding="utf-8")).get("narrative")
        texts += [n["th"], n["en"]] if n else []
    if (rel / "methods.json").exists():
        for t in json.loads((rel / "methods.json").read_text(encoding="utf-8"))["topics"]:
            texts += [t["note"]["th"], t["note"]["en"]] if t.get("note") else []
    site = tmp_path / "site"
    publish({**cfg, "publish": {**cfg["publish"], "site_url": "https://example.github.io/atlas/"}}, site=site)
    for feed in (site / "data" / "feeds").rglob("*.xml"):
        for e in ET.parse(feed).getroot().iter("{http://www.w3.org/2005/Atom}entry"):
            texts += [e.find("{http://www.w3.org/2005/Atom}title").text, e.find("{http://www.w3.org/2005/Atom}summary").text]
    assert ov["executive"]["bullets_th"] and len(texts) > 10                   # the real release has policy notes
    topics = json.loads((rel / "topics.json").read_text(encoding="utf-8"))["topics"]
    names = [n for t in topics for n in (t["th"], t["en"]) if n]
    bad = {t: jargon_in(t, names) for t in texts if jargon_in(t, names)}
    assert bad == {}, bad
