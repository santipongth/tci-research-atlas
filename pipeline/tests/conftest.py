from __future__ import annotations

from pathlib import Path

import pytest

from atlas.config import load_config

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def thaijo_dir() -> Path:
    return FIXTURES / "thaijo_md"


@pytest.fixture
def make_cfg(tmp_path):
    """cfg factory with all dirs inside tmp_path; usage: cfg = make_cfg(input_path, "thaijo_md")."""
    def _make(input_path: Path, fmt: str = "thaijo_md") -> dict:
        cfg = load_config(None)
        cfg["pipeline"].update(work_dir=str(tmp_path / "work"), output_dir=str(tmp_path / "out"),
                               state_dir=str(tmp_path / "state"))
        cfg["input"].update(path=str(input_path), format=fmt, workers=1)
        cfg["embedding"]["provider"] = "lite"           # CPU-only test embeddings (production default: local)
        return cfg
    return _make


@pytest.fixture(autouse=True, scope="session")
def _offline():
    """No test touches the network: OpenAlex calls raise OpenAlexUnavailable → taxonomy falls back.

    Session scope, so it is already active while module-scoped fixtures run the pipeline.
    """
    mp = pytest.MonkeyPatch()
    mp.setenv("ATLAS_OFFLINE", "1")
    yield
    mp.undo()
