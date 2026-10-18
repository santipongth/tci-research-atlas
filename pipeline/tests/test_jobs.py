"""Long-job plumbing (atlas.jobs): PID liveness, run lock, stop flag, atomic progress, background spawn."""
from __future__ import annotations

import errno
import json
import os
import socket
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
    lock_state,
    now_iso,
    pid_alive,
    process_start_time,
    python_command,
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
        write_json_atomic(f, {"n": 2}, timeout=0.05)   # must not raise (Windows: may skip)
    assert write_json_atomic(f, {"n": 3})
    assert read_json(f) == {"n": 3}


# ---------- RunLock: exclusivity comes from an OS lock on <dir>/.lock; run.lock is information only
HOLDER = """
import sys, time
from atlas.jobs import RunLock
lock = RunLock(sys.argv[1], log=lambda m: None).acquire()
print("READY", flush=True)
time.sleep(float(sys.argv[2]))
"""

RACER = """
import json, sys, time
from atlas.jobs import LockHeld, RunLock
path, t0, rounds, slot = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
out = []
for i in range(rounds):
    t = t0 + i * slot
    while time.time() < t:
        pass
    try:
        lk = RunLock(path, wait=0, log=lambda m: None).acquire()
        a = time.time()
        time.sleep(slot * 0.4)
        b = time.time()
        lk.release()
        out.append([i, a, b])
    except LockHeld:
        out.append([i, None, None])
print(json.dumps(out), flush=True)
"""


def _holder(lock_path, seconds=60):
    exe, env = python_command()          # the base interpreter: p.pid is the process that holds the lock
    p = subprocess.Popen([exe, "-c", HOLDER, str(lock_path), str(seconds)], stdout=subprocess.PIPE, text=True,
                         env=env)
    assert p.stdout.readline().strip() == "READY"
    return p


def test_lock_acquire_release(tmp_path):
    lock = RunLock(tmp_path / "run.lock").acquire()
    info = json.loads((tmp_path / "run.lock").read_text(encoding="utf-8"))
    assert info["pid"] == os.getpid() and info["host"] and info["started_at"]
    assert info["pid_started"] == process_start_time(os.getpid())          # defeats PID reuse in status
    lock.release()
    assert not (tmp_path / "run.lock").exists()
    assert (tmp_path / ".lock").exists()                                     # the OS-lock file is never deleted
    RunLock(tmp_path / "run.lock").acquire().release()                       # re-acquirable


def test_second_lock_in_the_same_process_is_refused(tmp_path):
    with RunLock(tmp_path / "run.lock"):
        with pytest.raises(LockHeld) as e:
            RunLock(tmp_path / "run.lock", wait=0).acquire()
    assert e.value.pid == os.getpid()


def test_two_processes_racing_never_both_hold_the_lock(tmp_path):
    lock_path = tmp_path / "run.lock"
    lock_path.write_text(json.dumps({"pid": 999_999, "host": socket.gethostname(),        # a stale info file,
                                     "started_at": "2020-01-01T00:00:00+00:00"}),          # as in the review probe
                         encoding="utf-8")
    rounds, slot = 20, 0.25
    t0 = time.time() + 2.5
    procs = [subprocess.Popen([sys.executable, "-c", RACER, str(lock_path), str(t0), str(rounds), str(slot)],
                              stdout=subprocess.PIPE, text=True) for _ in range(2)]
    results = [json.loads(p.communicate(timeout=60)[0]) for p in procs]
    for i in range(rounds):
        winners = [r[i] for r in results if r[i][1] is not None]
        assert len(winners) == 1, f"round {i}: {winners}"
    spans = sorted((a, b) for r in results for _, a, b in r if a is not None)
    assert all(spans[k][1] <= spans[k + 1][0] for k in range(len(spans) - 1))   # never two holders at once


def test_live_holder_with_a_stale_heartbeat_is_not_taken_over(tmp_path):
    lock_path = tmp_path / "run.lock"
    p = _holder(lock_path)
    try:
        old = "2020-01-01T00:00:00+00:00"
        write_json_atomic(tmp_path / "progress.json", {"pid": p.pid, "status": "running", "updated_at": old})
        with pytest.raises(LockHeld) as e:
            RunLock(lock_path, stale_seconds=300, heartbeat=tmp_path / "progress.json", wait=0).acquire()
        assert e.value.pid == p.pid and "hung" in str(e.value)
        st = job_status(tmp_path, stale_seconds=300)
        assert st["status"] == "hung" and st["lock_alive"] is True
        assert "hung" in format_job_status(st)
    finally:
        p.kill()
        p.wait()


def test_killed_holder_is_taken_over_at_once(tmp_path):
    lock_path = tmp_path / "run.lock"
    p = _holder(lock_path)
    p.kill()
    p.wait()
    logs = []
    t = time.monotonic()
    lock = RunLock(lock_path, stale_seconds=300, log=logs.append).acquire()   # no waiting for lock_stale_seconds
    assert time.monotonic() - t < 2
    assert json.loads(lock_path.read_text(encoding="utf-8"))["pid"] == os.getpid()
    assert logs and "stale" in logs[0] and str(p.pid) in logs[0]
    lock.release()


def test_info_file_alone_never_blocks(tmp_path):
    # a run.lock left by a dead run whose PID now belongs to someone else: no OS lock -> not running
    (tmp_path / "run.lock").write_text(json.dumps({"pid": os.getpid(), "host": socket.gethostname(),
                                                   "started_at": now_iso()}), encoding="utf-8")
    RunLock(tmp_path / "run.lock", log=lambda m: None).acquire().release()


def test_pid_reuse_is_detected_by_the_start_time(tmp_path):
    (tmp_path / "run.lock").write_text(json.dumps({"pid": os.getpid(), "host": socket.gethostname(),
                                                   "started_at": now_iso(), "pid_started": 12345}),
                                       encoding="utf-8")
    assert lock_state(tmp_path / "run.lock", None, 300)["alive"] is False
    write_json_atomic(tmp_path / "progress.json", {"status": "running", "updated_at": now_iso()})
    assert job_status(tmp_path)["status"] == "interrupted"


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


def test_stop_flag_clear_if_older(tmp_path):
    flag = StopFlag(tmp_path / "stop.flag")
    flag.request()
    os.utime(flag.path, (time.time() - 3600, time.time() - 3600))
    assert flag.clear_if_older(time.time() - 60) and not flag.is_set()      # stale: from an earlier run
    flag.request()
    assert not flag.clear_if_older(time.time() - 60) and flag.is_set()      # requested for this run: honoured


# ---------- Windows: replace/unlink while another process reads the file
def test_replace_and_unlink_retry_while_a_reader_holds_the_file(tmp_path):
    import threading

    from atlas.io_utils import replace_with_retry, unlink_with_retry

    dst = tmp_path / "index.parquet"
    dst.write_bytes(b"old")
    src = tmp_path / "index.tmp.parquet"
    src.write_bytes(b"new")
    f = open(dst, "rb")
    threading.Timer(0.4, f.close).start()                # `atlas status` reading at the wrong moment
    replace_with_retry(src, dst, timeout=10)
    assert dst.read_bytes() == b"new"
    g = open(dst, "rb")
    threading.Timer(0.4, g.close).start()
    assert unlink_with_retry(dst, timeout=10) and not dst.exists()
    assert unlink_with_retry(dst)                         # already gone: fine


@pytest.mark.skipif(os.name != "nt", reason="POSIX lets you replace/unlink an open file")
def test_replace_gives_up_after_the_timeout(tmp_path):
    from atlas.io_utils import replace_with_retry, unlink_with_retry

    dst, src = tmp_path / "a", tmp_path / "b"
    dst.write_bytes(b"1")
    src.write_bytes(b"2")
    with open(dst, "rb"):
        with pytest.raises(PermissionError):
            replace_with_retry(src, dst, timeout=0.3)
        assert unlink_with_retry(dst, timeout=0.3) is False


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
    spawned = spawn_background(["-c", code], log, cwd=tmp_path)
    for _ in range(200):
        if out.exists() and out.stat().st_size:
            break
        time.sleep(0.05)
    child = json.loads(out.read_text())
    assert child["pid"] == spawned.pid                            # the PID we print is the one that runs
    assert spawned.proc.wait(10) == 0
    if os.name == "nt":
        assert spawned.breakaway or spawned.warning is not None   # never silently left in a kill-on-close job
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


# ---------- fix round 2
def _lock_func():
    if os.name == "nt":
        import msvcrt

        return msvcrt, "locking"
    import fcntl

    return fcntl, "flock"


@pytest.mark.parametrize("err", [errno.ENOLCK, getattr(errno, "EOPNOTSUPP", 95), errno.EIO])
def test_a_filesystem_without_locking_is_a_clear_error(tmp_path, monkeypatch, err):
    from atlas.jobs import LockUnsupported

    mod, name = _lock_func()

    def broken(*a, **k):
        raise OSError(err, os.strerror(err))
    monkeypatch.setattr(mod, name, broken)
    with pytest.raises(LockUnsupported, match="local disk"):
        RunLock(tmp_path / "run.lock", wait=0).acquire()


@pytest.mark.parametrize("err", [errno.EACCES, errno.EAGAIN, getattr(errno, "EDEADLK", 36)])
def test_lock_conflict_errnos_mean_held(tmp_path, monkeypatch, err):
    mod, name = _lock_func()

    def held(*a, **k):
        raise OSError(err, os.strerror(err))
    monkeypatch.setattr(mod, name, held)
    with pytest.raises(LockHeld):
        RunLock(tmp_path / "run.lock", wait=0).acquire()


def test_os_lock_held_probe(tmp_path):
    from atlas.jobs import os_lock_held

    assert os_lock_held(tmp_path) is False                     # never ran: no .lock, nothing created
    assert not (tmp_path / ".lock").exists()
    with RunLock(tmp_path / "run.lock"):
        (tmp_path / "run.lock").unlink()                       # the informational file may be missing
        assert os_lock_held(tmp_path) is True
        st = job_status(tmp_path)
        assert st["lock_alive"] is True
    assert os_lock_held(tmp_path) is False


def test_acquire_releases_the_os_lock_when_writing_run_lock_fails(tmp_path, monkeypatch):
    import atlas.jobs as jobs

    def boom(*a, **k):
        raise ValueError("disk exploded")
    monkeypatch.setattr(jobs, "write_json_atomic", boom)
    with pytest.raises(ValueError):
        RunLock(tmp_path / "run.lock").acquire()
    monkeypatch.undo()
    RunLock(tmp_path / "run.lock", wait=0).acquire().release()  # not leaked: acquirable again at once


# ---------- fix round 3
@pytest.mark.skipif(os.name != "nt", reason="Windows sharing semantics")
def test_replace_blocked_predicts_os_replace_for_every_holder_kind(tmp_path):
    import ctypes
    import mmap
    from ctypes import wintypes

    from atlas.io_utils import replace_blocked

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                wintypes.DWORD, wintypes.HANDLE)
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    tgt, src = tmp_path / "index.parquet", tmp_path / "index.tmp.parquet"
    tgt.write_bytes(b"x" * 4096)

    def replace_fails():
        src.write_bytes(b"y" * 4096)
        try:
            os.replace(src, tgt)
            return False
        except PermissionError:
            src.unlink()
            return True

    def share_rwd():                                   # GENERIC_READ, share read|write|delete (AV/backup agents)
        return k32.CreateFileW(str(tgt), 0x80000000, 0x7, None, 3, 0x80, None)

    def mapped():                                      # a memory map whose file handle is already closed
        f = open(tgt, "rb")
        m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        f.close()
        return m

    cases = [("none", lambda: None, lambda h: None),
             ("plain open", lambda: open(tgt, "rb"), lambda h: h.close()),
             ("share read|write|delete", share_rwd, lambda h: k32.CloseHandle(h)),
             ("mmap", mapped, lambda m: m.close())]
    for name, opener, closer in cases:
        h = opener()
        try:
            predicted, actual = replace_blocked(tgt), replace_fails()
        finally:
            closer(h)
        assert predicted == actual, name
        assert actual == (name != "none"), name
