import json
from datetime import date, datetime

import pytest

import atlas.state as state
from atlas.state import (
    ReleaseMismatch,
    current_release,
    default_release,
    known_releases,
    previous_release,
    recorded_release,
    release_dir,
    release_from_date,
    snapshot_at,
    work_release,
)


def _clustered(cfg, release, snapshot="2026-11-20T10:15:00+07:00"):
    """work_dir as the cluster step leaves it: 04_topics_meta.json names the release and the snapshot."""
    from pathlib import Path

    work = Path(cfg["pipeline"]["work_dir"])
    work.mkdir(parents=True, exist_ok=True)
    (work / "04_topics_meta.json").write_text(json.dumps({"release": release, "snapshot_at": snapshot}),
                                              encoding="utf-8")


def test_work_release_is_the_clustered_release_and_refuses_another(make_cfg, tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    monkeypatch.setattr(state, "today", lambda: date(2027, 2, 3))        # the run is continued next quarter
    assert recorded_release(cfg) is None and work_release(cfg) == "2027Q1"   # nothing clustered yet: today's
    _clustered(cfg, "2026Q4")
    assert work_release(cfg) == "2026Q4" and default_release(cfg) == "2026Q4"   # null → the recorded release
    assert current_release(cfg) == "2027Q1"                                  # (what a NEW cluster run would use)
    for other in ("2027Q1", "2026Q3"):                                       # phantom / overwrite an older release
        cfg["pipeline"]["release"] = other
        with pytest.raises(ReleaseMismatch, match=f"work_dir was clustered for 2026Q4 but pipeline.release is "
                                                  f"{other} — re-run from cluster, or set pipeline.release: 2026Q4"):
            work_release(cfg)
        assert default_release(cfg) == other                               # validate/publish: as configured
    cfg["pipeline"]["release"] = "2026Q4"
    assert work_release(cfg) == "2026Q4"
    assert isinstance(ReleaseMismatch("x"), ValueError)                  # python -m atlas.pipeline prints it


def test_snapshot_is_recorded_once_and_reused(make_cfg, tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    before = datetime.now().astimezone()
    assert snapshot_at(cfg) >= before.replace(microsecond=0)           # no record: now
    _clustered(cfg, "2026Q4", "2026-11-20T10:15:00+07:00")
    snap = snapshot_at(cfg)
    assert (snap.year, snap.month, snap.day, snap.hour) == (2026, 11, 20, 10) and snap.utcoffset().seconds == 7 * 3600


def test_previous_release_of_an_explicit_release(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    for rel in ("2026Q1", "2026Q2", "2026Q3"):
        release_dir(cfg, rel, create=True)
    cfg["pipeline"]["release"] = "2026Q3"
    assert previous_release(cfg) == "2026Q2" and previous_release(cfg, "2026Q2") == "2026Q1"
    assert previous_release(cfg, "2026Q1") is None and previous_release(cfg, "2027Q1") == "2026Q3"


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
