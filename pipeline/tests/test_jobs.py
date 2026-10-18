"""Long-job plumbing (atlas.jobs): PID liveness, run lock, stop flag, atomic progress, background spawn."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from atlas.jobs import (
    LockHeld,
    ProgressFile,
    RunLock,
    StopFlag,
    find_jobs,
    format_job_status,
    job_status,
    now_iso,
    pid_alive,
    read_json,
    spawn_background,
    write_json_atomic,
)


def _dead_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


# ---------- pid_alive
def test_pid_alive_for_self_and_dead_process():
    assert pid_alive(os.getpid())
    assert not pid_alive(_dead_pid())
    assert not pid_alive(0) and not pid_alive(-5)


def test_pid_alive_does_not_kill_the_process():
    # on Windows os.kill(pid, 0) would TerminateProcess — pid_alive must only query
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        assert pid_alive(p.pid)
        time.sleep(0.2)
        assert p.poll() is None
    finally:
        p.kill()
        p.wait()


# ---------- write_json_atomic / read_json
def test_write_json_atomic_roundtrip(tmp_path):
    f = tmp_path / "progress.json"
    assert write_json_atomic(f, {"status": "running", "th": "\N{THAI CHARACTER KO KAI}"})
    assert read_json(f) == {"status": "running", "th": "\N{THAI CHARACTER KO KAI}"}
    assert [p.name for p in tmp_path.iterdir()] == ["progress.json"]          # no tmp file left
    assert read_json(tmp_path / "missing.json") is None
    (tmp_path / "bad.json").write_text("{half", encoding="utf-8")
    assert read_json(tmp_path / "bad.json") is None


def test_write_json_atomic_survives_an_open_reader(tmp_path):
    f = tmp_path / "progress.json"
    write_json_atomic(f, {"n": 1})
    with open(f, encoding="utf-8"):                     # `atlas status` reading at the wrong moment
        write_json_atomic(f, {"n": 2}, retries=2, retry_delay=0.01)   # must not raise (Windows: may skip)
    assert write_json_atomic(f, {"n": 3})
    assert read_json(f) == {"n": 3}


# ---------- RunLock
def test_lock_acquire_release(tmp_path):
    lock = RunLock(tmp_path / "run.lock").acquire()
    info = json.loads((tmp_path / "run.lock").read_text(encoding="utf-8"))
    assert info["pid"] == os.getpid() and info["host"] and info["started_at"]
    lock.release()
    assert not (tmp_path / "run.lock").exists()


def test_lock_held_by_live_pid_is_refused(tmp_path):
    with RunLock(tmp_path / "run.lock"):
        with pytest.raises(LockHeld) as e:
            RunLock(tmp_path / "run.lock").acquire()
    assert e.value.pid == os.getpid()


def test_lock_with_dead_pid_is_taken_over(tmp_path):
    (tmp_path / "run.lock").write_text(json.dumps({"pid": _dead_pid(), "host": __import__("socket").gethostname(),
                                                   "started_at": now_iso()}), encoding="utf-8")
    logs = []
    lock = RunLock(tmp_path / "run.lock", log=logs.append).acquire()
    assert json.loads((tmp_path / "run.lock").read_text(encoding="utf-8"))["pid"] == os.getpid()
    assert logs and "stale" in logs[0]
    lock.release()


def test_lock_with_live_pid_but_old_heartbeat_is_taken_over(tmp_path):
    old = "2020-01-01T00:00:00+00:00"
    (tmp_path / "run.lock").write_text(json.dumps({"pid": os.getpid(), "host": __import__("socket").gethostname(),
                                                   "started_at": old}), encoding="utf-8")
    write_json_atomic(tmp_path / "progress.json", {"pid": os.getpid(), "updated_at": old})
    lock = RunLock(tmp_path / "run.lock", stale_seconds=300, heartbeat=tmp_path / "progress.json",
                   log=lambda m: None).acquire()
    lock.release()


def test_lock_release_keeps_someone_elses_lock(tmp_path):
    lock = RunLock(tmp_path / "run.lock").acquire()
    (tmp_path / "run.lock").write_text(json.dumps({"pid": 999_999, "host": "x", "started_at": now_iso()}),
                                       encoding="utf-8")
    lock.release()
    assert (tmp_path / "run.lock").exists()


# ---------- StopFlag
def test_stop_flag(tmp_path):
    flag = StopFlag(tmp_path / "stop.flag")
    assert not flag.is_set()
    flag.request()
    assert flag.is_set() and StopFlag(tmp_path / "stop.flag").is_set()
    flag.clear()
    assert not flag.is_set()
    flag.clear()                                         # idempotent


# ---------- ProgressFile throttling
def test_progress_file_throttles_unless_forced_or_status_changes(tmp_path):
    t = {"now": 0.0}
    pf = ProgressFile(tmp_path / "progress.json", min_interval=30.0, clock=lambda: t["now"])
    assert pf.write({"status": "running", "n": 1})                     # first write always
    t["now"] = 10.0
    assert not pf.write({"status": "running", "n": 2})                 # throttled
    assert pf.write({"status": "backing_off", "n": 3})                 # status change
    assert pf.write({"status": "backing_off", "n": 4}, force=True)     # forced (flush)
    t["now"] = 41.0
    assert pf.write({"status": "backing_off", "n": 5})                 # interval elapsed
    assert read_json(tmp_path / "progress.json")["n"] == 5


# ---------- background spawn
def test_spawn_background_logs_and_reports_the_real_pid(tmp_path):
    out = tmp_path / "child.json"
    code = ("import json, os, sys; print('hello from child \\N{THAI CHARACTER KO KAI}'); sys.stdout.flush(); "
            f"json.dump({{'pid': os.getpid(), 'prefix': sys.prefix}}, open(r'{out}', 'w'))")
    log = tmp_path / "logs" / "run.log"
    pid = spawn_background(["-c", code], log, cwd=tmp_path)
    for _ in range(200):
        if out.exists() and out.stat().st_size:
            break
        time.sleep(0.05)
    child = json.loads(out.read_text())
    assert child["pid"] == pid                                    # the PID we print is the one that runs
    assert Path(child["prefix"]) == Path(sys.prefix)              # same environment (venv)
    for _ in range(100):
        if "hello from child" in log.read_text(encoding="utf-8", errors="replace"):
            break
        time.sleep(0.05)
    assert "hello from child" in log.read_text(encoding="utf-8", errors="replace")


# ---------- status discovery
def test_job_status_marks_a_dead_running_job_interrupted(tmp_path):
    job = tmp_path / "embeddings" / "api_m-1234"
    job.mkdir(parents=True)
    write_json_atomic(job / "progress.json", {"kind": "embedding", "store_id": "api|m|None", "status": "running",
                                              "pid": 1, "total": 10, "cached": 2, "embedded": 3, "remaining": 5,
                                              "updated_at": now_iso()})
    (job / "run.lock").write_text(json.dumps({"pid": _dead_pid(), "host": __import__("socket").gethostname(),
                                              "started_at": now_iso()}), encoding="utf-8")
    assert find_jobs(tmp_path) == [job]
    info = job_status(job)
    assert info["status"] == "interrupted" and info["lock_alive"] is False
    text = format_job_status(info)
    assert "interrupted" in text and "api|m|None" in text and "5" in text


def test_job_status_running_with_live_lock(tmp_path):
    write_json_atomic(tmp_path / "progress.json", {"status": "running", "updated_at": now_iso()})
    with RunLock(tmp_path / "run.lock"):
        assert job_status(tmp_path)["status"] == "running"
    write_json_atomic(tmp_path / "progress.json", {"status": "done", "updated_at": now_iso()})
    assert job_status(tmp_path)["status"] == "done"


def test_format_shows_starting_before_totals_are_known():
    text = format_job_status({"kind": "embedding", "store_id": "s", "status": "running", "total": 0, "remaining": 0})
    assert "starting" in text and "0 / 0 docs" not in text


def test_fmt_duration():
    from atlas.jobs import fmt_duration

    assert fmt_duration(0.34) == "0.3s" and fmt_duration(42) == "42s"
    assert fmt_duration(80) == "1m 20s" and fmt_duration(3 * 3600 + 120) == "3h 02m" and fmt_duration(None) == "-"
