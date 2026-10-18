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
