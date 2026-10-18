"""`atlas embed` / `atlas status` / `atlas embed-status` / `atlas embed-stop` (stub server, no network)."""
from __future__ import annotations

import json
import os
import threading
import time

import pandas as pd
import pytest
import yaml
from typer.testing import CliRunner

from atlas.cli import app
from atlas.embed_store import EmbeddingStore, store_dir
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
