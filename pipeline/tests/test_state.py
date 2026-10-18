from datetime import date

import pytest

from atlas.state import current_release, known_releases, previous_release, release_dir, release_from_date


def test_release_from_date_quarters():
    assert release_from_date(date(2026, 1, 5)) == "2026Q1"
    assert release_from_date(date(2026, 10, 18)) == "2026Q4"


def test_previous_release_tracks_index(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q1"
    assert previous_release(cfg) is None
    release_dir(cfg, create=True)
    cfg["pipeline"]["release"] = "2026Q2"
    assert previous_release(cfg) == "2026Q1"
    d = release_dir(cfg, create=True)
    assert d.name == "2026Q2" and d.is_dir()
    release_dir(cfg, create=True)                      # re-run of the same release: no duplicate
    assert known_releases(cfg) == ["2026Q1", "2026Q2"]
    assert previous_release(cfg) == "2026Q1"           # still the one BEFORE the current release
    cfg["pipeline"]["release"] = "2026Q1"
    assert previous_release(cfg) is None


def test_bad_release_name_rejected(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "../evil"
    with pytest.raises(ValueError):
        current_release(cfg)


def test_explicit_release_name_is_validated_too(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    for bad in ("../x", "2026Q1\n"):
        with pytest.raises(ValueError, match="invalid release name"):
            release_dir(cfg, bad, create=True)
    assert not (tmp_path / "state" / "x").exists() and known_releases(cfg) == []
