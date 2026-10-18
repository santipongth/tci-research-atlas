from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def thaijo_dir() -> Path:
    return FIXTURES / "thaijo_md"
