"""`atlas embed` / `atlas status` / `atlas embed-status` / `atlas embed-stop` (stub server, no network)."""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time

import pandas as pd
import pytest
import yaml
from typer.testing import CliRunner

from atlas.cli import app
from atlas.embed_store import EmbeddingStore, store_dir, text_key
from atlas.io_utils import write_table
from atlas.jobs import RunLock, now_iso, pid_alive, read_json, write_json_atomic
from tests.conftest import FIXTURES
from tests.stub_embed_server import StubEmbedServer

KEY_ENV = "ATLAS_TEST_EMBED_KEY"
STORE_ID = "api|stub-bge-m3|None"


def write_cfg(tmp_path, base_url="http://127.0.0.1:9/v1", input_path=None, **api) -> str:
    cfg = {
        "pipeline": {"work_dir": str(tmp_path / "work"), "output_dir": str(tmp_path / "out"),
                     "state_dir": str(tmp_path / "state")},
        "input": {"path": str(input_path or tmp_path / "corpus"), "workers": 1},
        "embedding": {"provider": "api", "api": {
            "base_url": base_url, "model": "stub-bge-m3", "dimensions": None, "api_key_env": KEY_ENV,
            "batch_size": 32, "concurrency": 4, "backoff_initial": 0.01, "backoff_max": 0.05, **api}},
    }
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return str(p)


def write_docs(tmp_path, n: int) -> list[str]:
    texts = [f"synthetic article {i} on topic {i % 17}: rice, water, tourism, nursing {i * 31 % 997}"
             for i in range(n)]
    write_table(pd.DataFrame({"article_id": [f"a{i}" for i in range(n)], "doc_text": texts}),
                tmp_path / "work" / "02_docs.parquet")
    return texts


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv(KEY_ENV, "dummy-key")


def invoke(*args):
    return CliRunner().invoke(app, list(args))


def test_embed_help_lists_options():
    out = invoke("embed", "--help").output
    for opt in ("--check", "--dry-run", "--background", "--concurrency", "--config"):
        assert opt in out
    assert invoke("status", "--help").exit_code == 0
    assert invoke("embed-status", "--help").exit_code == 0
    assert invoke("embed-stop", "--help").exit_code == 0


def test_dry_run_on_the_eleven_fixtures(tmp_path, key):
    cfg = write_cfg(tmp_path, input_path=FIXTURES / "thaijo_md")       # base_url is unreachable: no network
    r = invoke("embed", "-c", cfg, "--dry-run")
    assert r.exit_code == 0, r.output
    n = len(pd.read_parquet(tmp_path / "work" / "02_docs.parquet"))   # ingest + preprocess ran first
    assert 0 < n <= 11
    assert f"documents      : {n:,}" in r.output and "cached         : 0" in r.output
    assert f"to embed       : {n:,}" in r.output and "tokens" in r.output and "characters" in r.output
    assert not store_dir(tmp_path / "state" / "embeddings", STORE_ID).exists()   # nothing created or paid


def test_status_with_nothing_run_yet(tmp_path):
    cfg = write_cfg(tmp_path)
    for cmd in ("status", "embed-status"):
        r = invoke(cmd, "-c", cfg)
        assert r.exit_code == 0 and "nothing has run yet" in r.output


def test_check_reports_dim_and_latency(tmp_path, key):
    with StubEmbedServer(dim=8) as srv:
        r = invoke("embed", "-c", write_cfg(tmp_path, srv.url), "--check")
    assert r.exit_code == 0, r.output
    assert "dim" in r.output and "8" in r.output and "latency" in r.output and STORE_ID in r.output


def test_check_with_a_rejected_key_exits_2(tmp_path, key):
    with StubEmbedServer(require_key="the-right-key") as srv:
        r = invoke("embed", "-c", write_cfg(tmp_path, srv.url), "--check")
    assert r.exit_code == 2 and KEY_ENV in r.output and "dummy-key" not in r.output


def test_permanent_error_during_a_run_exits_2(tmp_path, key):
    write_docs(tmp_path, 20)
    with StubEmbedServer(require_key="the-right-key") as srv:
        r = invoke("embed", "-c", write_cfg(tmp_path, srv.url))
    assert r.exit_code == 2 and "401" in r.output and KEY_ENV in r.output
    prog = read_json(store_dir(tmp_path / "state" / "embeddings", STORE_ID) / "progress.json")
    assert prog["status"] == "failed" and "401" in prog["last_error"]


def test_lock_held_exits_3(tmp_path, key):
    write_docs(tmp_path, 10)
    sdir = EmbeddingStore(tmp_path / "state" / "embeddings", STORE_ID).dir
    with RunLock(sdir / "run.lock"):                                     # another run holds the store
        r = invoke("embed", "-c", write_cfg(tmp_path))
        assert r.exit_code == 3 and "atlas status" in r.output and str(os.getpid()) in r.output
        r = invoke("embed", "-c", write_cfg(tmp_path), "--background")  # refused before spawning anything
        assert r.exit_code == 3


def test_foreground_stop_exits_130(tmp_path, key):
    write_docs(tmp_path, 300)
    sdir = store_dir(tmp_path / "state" / "embeddings", STORE_ID)
    with StubEmbedServer(latency=0.05) as srv:
        cfg = write_cfg(tmp_path, srv.url, batch_size=10, concurrency=1)
        threading.Timer(1.0, lambda: (sdir / "stop.flag").write_text("x", encoding="utf-8")).start()  # = embed-stop
        r = invoke("embed", "-c", cfg)
    assert r.exit_code == 130, r.output
    assert read_json(store_dir(tmp_path / "state" / "embeddings", STORE_ID) / "progress.json")["status"] == "stopped"


def test_integration_flaky_server_2k_docs(tmp_path, key):
    texts = write_docs(tmp_path, 2000)
    with StubEmbedServer(fail_rate=0.3, too_large_rate=0.05, seed=3) as srv:
        cfg = write_cfg(tmp_path, srv.url)
        r = invoke("embed", "-c", cfg)
        assert r.exit_code == 0, r.output
        assert srv.n_503 > 0 and srv.n_413 > 0
        assert set(srv.texts_served) == set(texts)
        meta = json.loads((tmp_path / "work" / "03_meta.json").read_text(encoding="utf-8"))
        assert meta["model_id"] == meta["store_id"] == STORE_ID and meta["n"] == 2000 and meta["n_retries"] > 0
        r2 = invoke("embed", "-c", cfg)
    assert r2.exit_code == 0 and "0 to embed" in r2.output
    st = invoke("status", "-c", cfg)
    assert st.exit_code == 0 and "done" in st.output and "2,000 / 2,000" in st.output


def _kill(pid):
    if pid and pid_alive(pid):
        import signal

        os.kill(pid, signal.SIGTERM)          # Windows: TerminateProcess


def test_background_run_then_embed_stop(tmp_path, key):
    write_docs(tmp_path, 600)
    sdir = store_dir(tmp_path / "state" / "embeddings", STORE_ID)
    with StubEmbedServer(latency=0.2) as srv:                # 60 sequential batches: ~12 s if never stopped
        cfg = write_cfg(tmp_path, srv.url, batch_size=10, concurrency=1)
        r = invoke("embed", "-c", cfg, "--background")
        assert r.exit_code == 0, r.output
        pid = int(next(line.split("PID")[1].split()[0] for line in r.output.splitlines() if "PID" in line))
        try:
            for _ in range(600):                              # the detached child is embedding
                if len(srv.texts_served) >= 20:
                    break
                time.sleep(0.05)
            prog = read_json(sdir / "progress.json") or {}
            assert prog.get("pid") == pid and prog.get("status") in ("running", "backing_off")
            assert "running" in invoke("status", "-c", cfg).output
            s = invoke("embed-stop", "-c", cfg)
            assert s.exit_code == 0, s.output
            for _ in range(600):
                if not pid_alive(pid):
                    break
                time.sleep(0.05)
            assert not pid_alive(pid)
            assert read_json(sdir / "progress.json")["status"] in ("stopped", "done")
            log = (sdir / "run.log").read_text(encoding="utf-8")
            assert "[embed]" in log and "to embed" in log
        finally:
            _kill(pid)


# ---------- fix round 1
def test_status_never_opens_the_files_of_a_live_run(tmp_path, monkeypatch):
    import atlas.embed_runner as er
    from atlas.cli import render_status
    from atlas.config import load_config

    cfg = load_config(write_cfg(tmp_path))
    sdir = EmbeddingStore(tmp_path / "state" / "embeddings", STORE_ID).dir

    def forbidden(*a, **k):
        raise AssertionError("status opened index.parquet/journal.bin of a live run")
    monkeypatch.setattr(er, "store_status_lines", forbidden)
    with RunLock(sdir / "run.lock"):
        write_json_atomic(sdir / "progress.json", {"kind": "embedding", "store_id": STORE_ID, "status": "running",
                                                   "pid": os.getpid(), "total": 10, "cached": 0, "embedded": 4,
                                                   "remaining": 6, "store_vectors": 3, "journal_pending": 1,
                                                   "truncated_total": 2, "updated_at": now_iso()})
        text = render_status(cfg)
    assert "running" in text and "3 vectors" in text and "1 vectors (go into the store" in text
    assert "2 in total" in text


def test_status_polling_during_a_live_run_never_breaks_it(tmp_path, key):
    from atlas.cli import render_status
    from atlas.config import load_config

    write_docs(tmp_path, 600)
    seen, stop = [], threading.Event()
    with StubEmbedServer(latency=0.01) as srv:
        cfg_path = write_cfg(tmp_path, srv.url, batch_size=8, concurrency=2, checkpoint_every=16)
        cfg = load_config(cfg_path)

        def poll():
            while not stop.is_set():
                seen.append(render_status(cfg))           # what `atlas status` prints, every 5 ms
                time.sleep(0.005)
        t = threading.Thread(target=poll, daemon=True)
        t.start()
        try:
            r = invoke("embed", "-c", cfg_path)
        finally:
            stop.set()
            t.join(10)
    assert r.exit_code == 0, r.output
    assert len(seen) > 20 and any("running" in x for x in seen)
    assert "done" in render_status(cfg)


def test_embed_stop_before_the_run_reaches_embedding_is_honoured(tmp_path, key):
    write_docs(tmp_path, 50)
    cfg = write_cfg(tmp_path)
    s = invoke("embed-stop", "-c", cfg)                    # e.g. a background run still ingesting
    assert s.exit_code == 0 and "will stop" in s.output
    r = invoke("embed", "-c", cfg)                         # this process started before the flag: honoured
    assert r.exit_code == 130, r.output
    assert not (store_dir(tmp_path / "state" / "embeddings", STORE_ID) / "stop.flag").exists()


def test_background_child_that_dies_at_once_is_reported(tmp_path, key, monkeypatch):
    monkeypatch.setenv("ATLAS_BACKGROUND_CHECK_S", "30")
    write_docs(tmp_path, 20)
    r = invoke("embed", "-c", write_cfg(tmp_path, "ftp://not-http.example/v1"), "--background")
    assert r.exit_code == 2, r.output
    assert "exit code 2" in r.output and "base_url" in r.output        # the tail of run.log is shown


def test_abandoned_requests_exit_at_once(tmp_path, monkeypatch):
    import atlas.cli as cli
    import atlas.pipeline as pl
    from atlas.config import load_config
    from atlas.jobs import RunStopped

    def stopped(cfg, steps):
        raise RunStopped("left", abandoned=3)
    codes = []

    def fake_exit(code):
        codes.append(code)
        raise SystemExit(code)
    monkeypatch.setattr(pl, "run", stopped)
    monkeypatch.setattr(cli.os, "_exit", fake_exit)
    with pytest.raises(SystemExit):
        cli._run_guarded(load_config(write_cfg(tmp_path)), ["embed"], None)
    assert codes == [130]                                   # no wait for the abandoned requests' threads


# ---------- fix round 2
def test_status_liveness_comes_from_the_os_lock_not_run_lock(tmp_path, monkeypatch):
    import atlas.embed_runner as er
    from atlas.cli import render_status
    from atlas.config import load_config

    cfg = load_config(write_cfg(tmp_path))
    sdir = EmbeddingStore(tmp_path / "state" / "embeddings", STORE_ID).dir

    def forbidden(*a, **k):
        raise AssertionError("status opened the files of a live run")
    monkeypatch.setattr(er, "store_status_lines", forbidden)
    with RunLock(sdir / "run.lock"):
        (sdir / "run.lock").unlink()                         # e.g. its write failed: information only
        write_json_atomic(sdir / "progress.json", {"kind": "embedding", "store_id": STORE_ID, "status": "running",
                                                   "pid": os.getpid(), "total": 4, "remaining": 2, "embedded": 2,
                                                   "store_vectors": 2, "updated_at": now_iso()})
        text = render_status(cfg)
    assert "running" in text and "2 vectors" in text


def test_final_store_failure_is_explained_not_a_traceback(tmp_path, monkeypatch):
    import atlas.cli as cli
    import atlas.pipeline as pl
    from atlas.config import load_config
    from atlas.embed_runner import StoreBusy

    def busy(cfg, steps):
        raise StoreBusy("index.parquet is held by another program; 120 vectors are kept in journal.bin")
    monkeypatch.setattr(pl, "run", busy)
    r = CliRunner().invoke(cli.app, ["run", "-c", write_cfg(tmp_path), "-s", "embed"])
    assert r.exit_code == 1 and "journal.bin" in r.output and "run the same command again" in r.output
    assert "Traceback" not in r.output
    assert cli._run_guarded(load_config(write_cfg(tmp_path)), ["embed"], None) == 1


def test_unsupported_locking_exits_2(tmp_path, key, monkeypatch):
    import atlas.jobs as jobs

    write_docs(tmp_path, 10)

    def unsupported(fd):
        raise jobs.LockUnsupported("cannot lock; put state_dir on a local disk")
    monkeypatch.setattr(jobs, "_os_lock", unsupported)
    r = invoke("embed", "-c", write_cfg(tmp_path))
    assert r.exit_code == 2 and "local disk" in r.output


DOUBLE_CTRL_C = """
import _thread, sys, threading, time
from pathlib import Path
cfg, trigger = sys.argv[1], Path(sys.argv[2])

def presses():
    while not trigger.exists():
        time.sleep(0.02)
    print("CHILD Ctrl-C 1", flush=True)
    _thread.interrupt_main()
    time.sleep(1.0)
    print("CHILD Ctrl-C 2", flush=True)
    _thread.interrupt_main()

threading.Thread(target=presses, daemon=True).start()
from atlas.cli import app
app(["embed", "-c", cfg], prog_name="atlas")
"""


def test_second_ctrl_c_exits_the_cli_at_once_end_to_end(tmp_path, key):
    from atlas.jobs import python_command

    texts = write_docs(tmp_path, 400)
    trigger = tmp_path / "press-now"
    with StubEmbedServer(latency=0.02) as srv:
        cfg = write_cfg(tmp_path, srv.url, batch_size=8, concurrency=2, checkpoint_every=10_000,
                        request_timeout=120.0)
        exe, env = python_command()
        p = subprocess.Popen([exe, "-c", DOUBLE_CTRL_C, cfg, str(trigger)], env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        try:
            for _ in range(600):                              # let some batches complete ...
                if len(srv.texts_served) >= 48:
                    break
                time.sleep(0.05)
            srv.latency = 60.0                                # ... then every request hangs for a minute
            time.sleep(0.3)
            trigger.write_text("go", encoding="utf-8")
            t_press = time.monotonic()
            out, _ = p.communicate(timeout=60)
            after_second = time.monotonic() - t_press - 1.0   # the 2nd press comes 1 s after the 1st
            served = set(srv.texts_served)                    # snapshot: slow requests never completed
        finally:
            if p.poll() is None:
                p.kill()
                p.wait()
    assert p.returncode == 130, out
    assert "abandoning" in out and after_second < 6.0, (after_second, out)
    store = EmbeddingStore(tmp_path / "state" / "embeddings", STORE_ID)
    stored = {t for t in texts if store.has(text_key(STORE_ID, t))}
    assert stored == served and len(stored) >= 48            # everything that completed was saved


# ---------- fix round 3
ERROR_ABANDON = """
import _thread, json, sys, threading, time
import atlas.embed_api as ea
n = {"i": 0}
lk = threading.Lock()

def transport(url, headers, body, timeout):
    inp = json.loads(body)["input"]
    with lk:
        n["i"] += 1
        i = n["i"]
    if i <= 4:
        return 200, {}, json.dumps({"data": [{"index": j, "embedding": [float(len(t))] * 8}
                                             for j, t in enumerate(inp)]}).encode()
    if i == 5:
        def presses():
            time.sleep(1.0)
            _thread.interrupt_main()
            time.sleep(1.0)
            print("CHILD second Ctrl-C", flush=True)
            _thread.interrupt_main()
        threading.Thread(target=presses, daemon=True).start()
        time.sleep(30.0)                                   # this request hangs
        return 200, {}, json.dumps({"data": [{"index": j, "embedding": [1.0] * 8} for j in range(len(inp))]}).encode()
    time.sleep(0.2)
    return 400, {}, b'{"error": "bad request"}'            # permanent

ea.urllib_transport = transport
from atlas.cli import app
app(["embed", "-c", sys.argv[1]], prog_name="atlas")
"""


def test_abandon_during_a_failing_run_still_exits_at_once(tmp_path, key):
    from atlas.jobs import python_command

    write_docs(tmp_path, 200)
    cfg = write_cfg(tmp_path, "http://127.0.0.1:9/v1", batch_size=8, concurrency=2, request_timeout=120.0)
    exe, env = python_command()
    t0 = time.monotonic()
    p = subprocess.Popen([exe, "-c", ERROR_ABANDON, cfg], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace")
    try:
        out, _ = p.communicate(timeout=90)
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()
    wall = time.monotonic() - t0
    assert p.returncode == 2, out                           # the run's own outcome (permanent error) is kept
    assert "abandoning" in out and "400" in out
    assert wall < 20, (wall, out)                           # not 30 s waiting for the abandoned request


def test_final_disk_full_is_explained(tmp_path, monkeypatch):
    import atlas.cli as cli
    import atlas.pipeline as pl
    from atlas.embed_runner import StoreSaveFailed

    def full(cfg, steps):
        raise StoreSaveFailed("could not save 120 vectors into the store (OSError: [Errno 28] No space left on "
                              "device) — they are kept in journal.bin; free space / fix the cause and run the same "
                              "command again")
    monkeypatch.setattr(pl, "run", full)
    r = CliRunner().invoke(cli.app, ["run", "-c", write_cfg(tmp_path), "-s", "embed"])
    assert r.exit_code == 1 and "journal.bin" in r.output and "No space left" in r.output
    assert "Traceback" not in r.output


def test_pid_unknown_when_run_lock_is_missing(tmp_path):
    sdir = EmbeddingStore(tmp_path / "state" / "embeddings", STORE_ID).dir
    with RunLock(sdir / "run.lock"):
        (sdir / "run.lock").unlink()
        s = invoke("embed-stop", "-c", write_cfg(tmp_path))
        b = invoke("embed", "-c", write_cfg(tmp_path), "--background")
    assert s.exit_code == 0 and "PID unknown" in s.output and "PID None" not in s.output
    assert b.exit_code == 3 and "PID unknown" in b.output and "PID None" not in b.output
