from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from atlas.config import AtlasConfig, load_config

PIPELINE = Path(__file__).resolve().parent.parent


def _keys(d, prefix=""):
    out = set()
    for k, v in d.items():
        out.add(prefix + k)
        if isinstance(v, dict) and k != "columns":
            out |= _keys(v, prefix + k + ".")
    return out


def test_defaults_load_and_paths_are_absolute():
    cfg = load_config(None)
    for k in ("work_dir", "output_dir", "state_dir"):
        assert Path(cfg["pipeline"][k]).is_absolute()
    assert cfg["emerging"]["definition_version"] == 3
    assert cfg["embedding"]["provider"] == "local"            # production default; lite is for CI/tests only
    assert cfg["embedding"]["lite_max_docs"] == 50_000


def test_example_yaml_is_valid_and_documents_every_key():
    raw = yaml.safe_load((PIPELINE / "config.example.yaml").read_text(encoding="utf-8"))
    AtlasConfig.model_validate(raw)
    assert _keys(raw) == _keys(AtlasConfig().model_dump())


def test_unknown_key_is_rejected(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("emerging:\n  recnt_window: 3\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="recnt_window"):
        load_config(p)


def test_bad_provider_is_rejected(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("embedding:\n  provider: magic\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(p)


def test_relative_paths_resolve_against_config_dir(tmp_path):
    p = tmp_path / "sub" / "c.yaml"
    p.parent.mkdir()
    p.write_text("pipeline:\n  work_dir: ./w\ninput:\n  path: ../data\n", encoding="utf-8")
    cfg = load_config(p)
    assert Path(cfg["pipeline"]["work_dir"]) == (tmp_path / "sub" / "w").resolve()
    assert Path(cfg["input"]["path"]) == (tmp_path / "data").resolve()


def test_ci_config_loads():
    cfg = load_config(PIPELINE / "configs" / "ci.yaml")
    assert cfg["embedding"]["provider"] == "lite"
    assert cfg["labeling"]["provider"] == "off"


# ---- Task 19: API embedding runner settings
def test_api_embed_defaults():
    api = load_config(None)["embedding"]["api"]
    assert api["api_key_env"] == "ATLAS_EMBED_API_KEY"
    assert api["model"] == "text-embedding-3-large" and api["store_id"] is None
    assert api["max_retries"] is None                    # unlimited retries on transient errors
    assert (api["batch_size"], api["max_batch_chars"], api["concurrency"]) == (32, 60_000, 4)
    assert (api["backoff_initial"], api["backoff_max"], api["request_timeout"]) == (2.0, 300.0, 120.0)
    assert (api["min_text_chars"], api["checkpoint_every"], api["lock_stale_seconds"]) == (512, 2000, 300)
    assert api["requests_per_minute"] is None


@pytest.mark.parametrize("bad", ["batch_size: 0", "concurrency: 0", "backoff_initial: 0",
                                 "backoff_initial: 10\n    backoff_max: 5", "requests_per_minute: 0"])
def test_api_embed_validation(tmp_path, bad):
    p = tmp_path / "c.yaml"
    p.write_text(f"embedding:\n  api:\n    {bad}\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(p)


def test_local_provider_has_its_own_lock_stale_seconds():
    assert load_config(None)["embedding"]["local"]["lock_stale_seconds"] == 300


def test_p1_sections_have_defaults():
    cfg = load_config(None)
    assert cfg["pipeline"]["release"] is None
    assert cfg["topics"]["mode"] == "auto" and cfg["taxonomy"]["source"] == "openalex"
    assert "completeness" not in cfg["emerging"]                    # definition v3 stays (user, 2026-10-19)
    assert cfg["validation"]["min_kept_ids"] == 0.9 and cfg["bakeoff"]["embedding_candidates"] == []


def test_release_name_and_reference_path(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("pipeline:\n  release: 2026Q4\ntaxonomy:\n  reference_path: ref/works.jsonl\n", encoding="utf-8")
    cfg = load_config(p)
    assert cfg["pipeline"]["release"] == "2026Q4"
    assert Path(cfg["taxonomy"]["reference_path"]) == (tmp_path / "ref" / "works.jsonl").resolve()
    p.write_text("pipeline:\n  release: ../x\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(p)
