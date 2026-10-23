"""`atlas quarterly`: the round config, the corpus manifest, the LLM confirmation and the upload-ready package."""
import json
import zipfile
from pathlib import Path

import pytest

from atlas import quarterly as q
from atlas.corpus_convert import convert_markdown

EXAMPLE = Path(__file__).resolve().parents[2] / "docs" / "corpus" / "example"


def _site(tmp_path: Path, provider: str) -> Path:
    site = tmp_path / "site"
    (site / "data" / "2026Q4").mkdir(parents=True)
    (site / "index.html").write_text("<!doctype html>", encoding="utf-8")
    (site / "atlas-offline.html").write_text("<!doctype html>", encoding="utf-8")
    (site / "data" / "latest.json").write_text(json.dumps({"release": "2026Q4", "path": "2026Q4/manifest.json"}),
                                               encoding="utf-8")
    (site / "data" / "2026Q4" / "manifest.json").write_text(
        json.dumps({"embedding_provider": provider}), encoding="utf-8")
    (site / "data" / "2026Q4" / "overview.json").write_text(json.dumps({"kpis": {"articles": 11}}), encoding="utf-8")
    return site


def test_round_config_takes_the_corpus_format_and_journals_from_the_folder():
    cfg = q.round_config(None, "2026Q4", EXAMPLE)
    assert cfg["input"]["format"] == "corpus_jsonl" and cfg["pipeline"]["release"] == "2026Q4"
    assert Path(cfg["journals"]["registry_path"]) == (EXAMPLE / "journals.csv").resolve()
    assert Path(cfg["institutions"]["aliases_path"]) == (EXAMPLE / "institutions_aliases.csv").resolve()
    assert cfg["institutions"]["population_path"] != str(EXAMPLE / "province_population.csv")   # not delivered


def test_round_config_refuses_a_missing_corpus(tmp_path):
    with pytest.raises(q.RoundError, match="corpus not found"):
        q.round_config(None, "2026Q4", tmp_path / "nope")


def test_corpus_manifest_hashes_every_data_file():
    m = q.corpus_manifest(q.round_config(None, "2026Q4", EXAMPLE))
    assert [f["path"] for f in m["files"]] == ["articles/part-0001.jsonl", "journals.csv", "institutions_aliases.csv"]
    assert all(len(f["sha256"]) == 64 for f in m["files"])


def test_package_makes_the_site_folder_and_two_zips(tmp_path):
    pkg = q.package(_site(tmp_path, "api"), "2026Q4", tmp_path / "deploy")
    assert (Path(pkg["site"]) / "index.html").is_file()
    with zipfile.ZipFile(pkg["data_zip"]) as z:
        files = sorted(n for n in z.namelist() if not n.endswith("/"))
        assert files == ["atlas-offline.html", "data/2026Q4/manifest.json", "data/2026Q4/overview.json", "data/latest.json"]
    with zipfile.ZipFile(pkg["site_zip"]) as z:
        assert "index.html" in z.namelist()


def test_package_reports_the_kpis_of_the_release(tmp_path):
    assert q.package(_site(tmp_path, "api"), "2026Q4", tmp_path / "deploy")["articles"] == {"articles": 11}


def test_an_unfinished_round_is_resumed_after_the_quarter_turns(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    monkeypatch.setattr("atlas.state.recorded_release", lambda cfg: "2026Q3")
    assert q.default_release(None, runs) == "2026Q3"                      # started, no summary → resume it
    (runs / "2026Q3").mkdir(parents=True)
    (runs / "2026Q3" / "summary.md").write_text("done", encoding="utf-8")
    assert q.default_release(None, runs) != "2026Q3"                      # finished → the next round is a new one


def test_package_refuses_sample_data(tmp_path):
    with pytest.raises(q.RoundError, match="tests only"):
        q.package(_site(tmp_path, "lite"), "2026Q4", tmp_path / "deploy")


def test_llm_cost_must_be_confirmed(tmp_path, monkeypatch, thaijo_dir):
    corpus = tmp_path / "corpus"
    convert_markdown(thaijo_dir, corpus)
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(f"pipeline:\n  work_dir: {tmp_path / 'w'}\n  output_dir: {tmp_path / 'o'}\n"
                        f"  state_dir: {tmp_path / 's'}\nembedding:\n  provider: lite\nlabeling:\n  provider: llm\n",
                        encoding="utf-8")
    calls = []
    monkeypatch.setattr(q, "_atlas", lambda args, log=None: calls.append(args[0]) or 0)
    with pytest.raises(q.RoundError, match="not confirmed"):
        q.run_round(cfg_file, corpus, "2026Q4", yes=False, strict=False, build=False, prepare=False,
                    runs_dir=tmp_path / "runs", deploy_dir=tmp_path / "deploy", site=tmp_path / "site",
                    confirm=lambda _: False)
    assert calls == ["profile", "llm"] and "run" not in calls          # nothing was paid for
    assert (tmp_path / "runs" / "2026Q4" / "config.yaml").is_file()
