"""Embedding runner (atlas.embed_runner): batching, concurrency, journal, lock, stop flag, progress."""
from __future__ import annotations

import _thread
import hashlib
import json
import os
import socket
import struct
import subprocess
import sys
import threading
import time

import numpy as np
import pytest
import yaml

from atlas.embed_api import ApiEmbedder, EmbeddingConfigError
from atlas.embed_runner import JOURNAL, pack_batches, read_journal, run_embedding
from atlas.embed_store import EmbeddingStore, text_key
from atlas.jobs import LockHeld, now_iso, read_json

DIM = 6


def fake_vec(text: str, dim: int = DIM) -> np.ndarray:
    d = hashlib.sha256(text.encode("utf-8")).digest()
    return np.frombuffer(d[:dim], dtype=np.uint8).astype(np.float32) + 1.0


class Fake:
    """Deterministic embedder; optional jitter (shuffles completion order), failure and hooks per call."""

    def __init__(self, model_id="fake|1", *, dim=DIM, jitter=0.0, fail_on_call=None, hook=None):
        self.model_id, self.dim, self.jitter = model_id, dim, jitter
        self.fail_on_call, self.hook = fail_on_call, hook
        self.calls, self.texts = 0, []
        self._lock = threading.Lock()

    def embed_batch(self, texts):
        with self._lock:
            self.calls += 1
            n = self.calls
            self.texts += list(texts)
        if self.hook:
            self.hook(n)
        if self.jitter:
            time.sleep(self.jitter * (hash(texts[0]) % 7) / 7)
        if self.fail_on_call and n == self.fail_on_call:
            raise RuntimeError("simulated non-retryable failure")
        return np.stack([fake_vec(t, self.dim) for t in texts])


TEXTS = [f"document number {i} about topic {i % 5}" for i in range(40)]


def rcfg(**kw):
    return {"batch_size": 4, "max_batch_chars": 10_000, "concurrency": 1, "checkpoint_every": 8,
            "lock_stale_seconds": 300, **kw}


def store_for(tmp_path, model_id="fake|1"):
    return EmbeddingStore(tmp_path / "embeddings", model_id)


def keys_of(texts, model_id="fake|1"):
    return [text_key(model_id, t) for t in texts]


# ---------- batch packing
def test_pack_batches_by_count_and_chars():
    assert pack_batches([1] * 10, 4, None) == [(0, 4), (4, 8), (8, 10)]
    assert pack_batches([5, 5, 5, 5], 10, 10) == [(0, 2), (2, 4)]
    assert pack_batches([3, 50, 3, 3], 10, 10) == [(0, 1), (1, 2), (2, 4)]     # a long text gets its own batch
    assert pack_batches([], 4, 10) == []


# ---------- basic run, concurrency, progress
def test_concurrency_one_and_four_give_identical_stores(tmp_path):
    a = store_for(tmp_path / "a")
    b = store_for(tmp_path / "b")
    sa = run_embedding(TEXTS, Fake(), a, rcfg(concurrency=1), progress=False)
    sb = run_embedding(TEXTS, Fake(jitter=0.01), b, rcfg(concurrency=4), progress=False)
    assert sa["status"] == sb["status"] == "done" and sa["embedded"] == sb["embedded"] == 40
    ks = keys_of(TEXTS)
    assert np.array_equal(a.get(ks), b.get(ks))
    assert np.array_equal(a.get(ks), np.stack([fake_vec(t) for t in TEXTS]))


def test_progress_json_fields_and_done(tmp_path):
    store = store_for(tmp_path)
    stats = run_embedding(TEXTS + TEXTS[:5], Fake(), store, rcfg(), progress=False)   # duplicates count once
    assert stats == {**stats, "total": 40, "cached": 0, "embedded": 40, "status": "done", "retries": 0,
                     "truncated": 0}
    prog = read_json(store.dir / "progress.json")
    for field in ("store_id", "status", "pid", "total", "cached", "embedded", "remaining", "rate_per_s", "eta_s",
                  "retries", "truncated", "last_error", "last_error_at", "started_at", "updated_at"):
        assert field in prog, field
    assert prog["status"] == "done" and prog["remaining"] == 0 and prog["store_id"] == "fake|1"
    assert not (store.dir / JOURNAL).exists() and not (store.dir / "run.lock").exists()


def test_second_run_embeds_nothing(tmp_path, capsys):
    store = store_for(tmp_path)
    run_embedding(TEXTS, Fake(), store, rcfg(), progress=False)
    again = Fake()
    stats = run_embedding(TEXTS, again, store_for(tmp_path), rcfg(), progress=False)
    assert again.calls == 0 and stats["cached"] == 40 and stats["status"] == "done"
    assert "0 to embed" in capsys.readouterr().out


# ---------- failures keep what was paid for
def test_failure_keeps_completed_batches_and_rerun_embeds_only_the_rest(tmp_path):
    store = store_for(tmp_path)
    with pytest.raises(RuntimeError, match="simulated"):
        run_embedding(TEXTS, Fake(fail_on_call=4), store, rcfg(checkpoint_every=1000), progress=False)
    kept = len(store_for(tmp_path))
    assert kept >= 12                                     # batches 1-3 at least (4 texts each)
    assert not (store.dir / JOURNAL).exists()             # flushed on the way out
    assert read_json(store.dir / "progress.json")["status"] == "failed"
    second = Fake()
    stats = run_embedding(TEXTS, second, store_for(tmp_path), rcfg(), progress=False)
    assert len(second.texts) == 40 - kept                 # nothing paid twice
    assert stats["status"] == "done" and len(store_for(tmp_path)) == 40


def test_dim_mismatch_with_existing_store_is_a_config_error(tmp_path):
    store = store_for(tmp_path)
    store.add(["k-old"], np.ones((1, 3), dtype=np.float32))
    with pytest.raises(EmbeddingConfigError, match="store_id"):
        run_embedding(TEXTS, Fake(dim=4), store, rcfg(), progress=False)


def test_store_dim_property(tmp_path):
    store = store_for(tmp_path)
    assert store.dim is None
    store.add(["a"], np.ones((1, 5), dtype=np.float32))
    assert store.dim == 5 and store_for(tmp_path).dim == 5


# ---------- journal
def _write_journal(path, keys, vecs, extra: bytes = b""):
    with open(path, "wb") as f:
        f.write(b"ATJ1" + struct.pack("<I", vecs.shape[1]))
        for k, v in zip(keys, vecs):
            f.write(k.encode("ascii") + v.astype("<f4").tobytes())
        f.write(extra)


def test_journal_recovery_skips_a_partial_record(tmp_path, capsys):
    store = store_for(tmp_path)
    ks = keys_of(TEXTS[:6])
    vecs = np.stack([fake_vec(t) for t in TEXTS[:6]])
    rec = ks[5].encode("ascii") + vecs[5].astype("<f4").tobytes()
    _write_journal(store.dir / JOURNAL, ks[:5], vecs[:5], extra=rec[: len(rec) // 2])
    fake = Fake()
    stats = run_embedding(TEXTS, fake, store, rcfg(), progress=False)
    assert "recovered 5 vectors from journal" in capsys.readouterr().out
    assert stats["recovered"] == 5 and stats["cached"] == 5 and len(fake.texts) == 35
    assert not (store.dir / JOURNAL).exists()
    assert np.array_equal(store.get(ks[:5]), vecs[:5])


def test_read_journal_ignores_damaged_records(tmp_path):
    ks = keys_of(TEXTS[:3])
    vecs = np.stack([fake_vec(t) for t in TEXTS[:3]])
    vecs[1, 0] = np.nan                                     # a damaged record is skipped, not stored
    _write_journal(tmp_path / JOURNAL, ks, vecs, extra=b"\x00" * (40 + 4 * DIM))   # zero-filled tail
    keys, arr, bad = read_journal(tmp_path / JOURNAL)
    assert keys == [ks[0], ks[2]] and bad == 2 and arr.shape == (2, DIM)


def test_journal_holds_batches_between_checkpoints(tmp_path):
    seen = {}
    store = store_for(tmp_path)

    def hook(n):
        if n == 4:                                         # 3 batches done, nothing checkpointed yet
            seen["journal"] = read_journal(store.dir / JOURNAL)[0]
            seen["store"] = len(store_for(tmp_path))
    run_embedding(TEXTS, Fake(hook=hook), store, rcfg(checkpoint_every=1000, concurrency=1), progress=False)
    assert seen["store"] == 0 and len(seen["journal"]) >= 8


# ---------- lock
def test_lock_held_by_a_live_pid_refuses_to_run(tmp_path):
    store = store_for(tmp_path)
    (store.dir / "run.lock").write_text(json.dumps({"pid": os.getpid(), "host": socket.gethostname(),
                                                    "started_at": now_iso()}), encoding="utf-8")
    with pytest.raises(LockHeld):
        run_embedding(TEXTS, Fake(), store, rcfg(), progress=False)
    assert (store.dir / "run.lock").exists()


def test_lock_of_a_dead_pid_is_taken_over(tmp_path):
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    store = store_for(tmp_path)
    (store.dir / "run.lock").write_text(json.dumps({"pid": p.pid, "host": socket.gethostname(),
                                                    "started_at": now_iso()}), encoding="utf-8")
    assert run_embedding(TEXTS, Fake(), store, rcfg(), progress=False)["status"] == "done"
    assert not (store.dir / "run.lock").exists()


# ---------- stopping
def test_stop_flag_mid_run_stops_and_flushes(tmp_path):
    store = store_for(tmp_path)

    def hook(n):
        if n == 3:
            (store.dir / "stop.flag").write_text("x", encoding="utf-8")     # what `atlas embed-stop` does
    fake = Fake(hook=hook)
    stats = run_embedding(TEXTS, fake, store, rcfg(checkpoint_every=1000), progress=False)
    assert stats["status"] == "stopped" and 0 < stats["embedded"] < 40
    assert len(store_for(tmp_path)) == stats["embedded"] == len(fake.texts)  # every paid vector flushed
    assert not (store.dir / "stop.flag").exists() and not (store.dir / JOURNAL).exists()
    assert read_json(store.dir / "progress.json")["status"] == "stopped"


def test_stale_stop_flag_at_start_is_ignored(tmp_path):
    store = store_for(tmp_path)
    (store.dir / "stop.flag").write_text("old", encoding="utf-8")
    assert run_embedding(TEXTS, Fake(), store, rcfg(), progress=False)["status"] == "done"


def test_ctrl_c_stops_cleanly(tmp_path):
    store = store_for(tmp_path)

    def hook(n):
        if n == 3:
            _thread.interrupt_main()                       # Ctrl-C arrives in the main thread
    fake = Fake(hook=hook)
    stats = run_embedding(TEXTS, fake, store, rcfg(checkpoint_every=1000), progress=False)
    assert stats["status"] == "stopped"
    assert len(store_for(tmp_path)) == len(fake.texts)


def _always_503(url, headers, body, timeout):
    return 503, {}, b"down"


def test_stop_during_a_long_backoff_is_prompt(tmp_path):
    cfg = {"embedding": {"api": {"base_url": "http://x/v1", "api_key_env": "NOPE_KEY", "model": "m",
                                 "dimensions": None, "store_id": None, "request_timeout": 5.0,
                                 "min_text_chars": 10, "backoff_initial": 60.0, "backoff_max": 60.0,
                                 "max_retries": None, "requests_per_minute": None}}}
    emb = ApiEmbedder(cfg, transport=_always_503)                   # real, interruptible backoff sleeps
    store = store_for(tmp_path, emb.model_id)
    threading.Timer(0.5, lambda: (store.dir / "stop.flag").write_text("x", encoding="utf-8")).start()
    t0 = time.monotonic()
    stats = run_embedding(TEXTS, emb, store, rcfg(concurrency=2), progress=False)
    assert time.monotonic() - t0 < 10
    assert stats["status"] == "stopped" and stats["retries"] >= 1
    prog = read_json(store.dir / "progress.json")
    assert prog["status"] == "stopped" and "503" in prog["last_error"]


def test_backing_off_status_is_reported(tmp_path):
    release = threading.Event()
    store = store_for(tmp_path)

    class Slow(Fake):
        on_event = None

        def embed_batch(self, texts):
            if not release.is_set():
                self.on_event("retry", {"attempt": 1, "delay": 30.0, "status": 503, "error": "HTTP 503: down"})
                release.wait(10)
            return super().embed_batch(texts)

    result = {}
    t = threading.Thread(target=lambda: result.update(run_embedding(TEXTS[:4], Slow(), store, rcfg(),
                                                                    progress=False)))
    t.start()
    try:
        for _ in range(100):
            prog = read_json(store.dir / "progress.json") or {}
            if prog.get("status") == "backing_off":
                break
            time.sleep(0.05)
        assert prog.get("status") == "backing_off" and "503" in (prog.get("last_error") or "")
    finally:
        release.set()
        t.join(10)
    assert result["status"] == "done"


# ---------- hard kill: a real process killed mid-run loses only in-flight requests
def test_hard_kill_then_resume(tmp_path, capsys):
    import pandas as pd

    from atlas.config import load_config
    from atlas.embed import embed
    from atlas.io_utils import write_table
    from tests.stub_embed_server import StubEmbedServer

    n = 300
    texts = [f"synthetic article {i}: rice, tourism and water management study {i * 7919 % 1000}" for i in range(n)]
    with StubEmbedServer(dim=8, latency=0.15) as srv:
        cfg_yaml = {
            "pipeline": {"work_dir": str(tmp_path / "work"), "output_dir": str(tmp_path / "out"),
                         "state_dir": str(tmp_path / "state")},
            "embedding": {"provider": "api", "api": {
                "base_url": srv.url, "model": "stub-bge-m3", "dimensions": None, "api_key_env": "ATLAS_TEST_KEY",
                "batch_size": 10, "concurrency": 2, "checkpoint_every": 100_000,
                "backoff_initial": 0.05, "backoff_max": 0.2}},
        }
        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text(yaml.safe_dump(cfg_yaml), encoding="utf-8")
        cfg = load_config(cfg_path)
        write_table(pd.DataFrame({"article_id": [f"a{i}" for i in range(n)], "doc_text": texts}),
                    tmp_path / "work" / "02_docs.parquet")
        store_dir = EmbeddingStore(tmp_path / "state" / "embeddings", "api|stub-bge-m3|None").dir
        journal = store_dir / JOURNAL
        rec = 40 + 4 * 8
        env = {**os.environ, "ATLAS_TEST_KEY": "dummy"}
        proc = subprocess.Popen([sys.executable, "-m", "atlas", "embed", "-c", str(cfg_path)], env=env,
                                cwd=str(tmp_path), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if journal.exists() and (journal.stat().st_size - 8) // rec >= 20:   # >= 2 batches journaled
                    break
                if proc.poll() is not None:
                    pytest.fail(f"embed process exited early ({proc.returncode})")
                time.sleep(0.05)
            else:
                pytest.fail("journal never reached 2 batches")
        finally:
            proc.kill()                                     # TerminateProcess on Windows: no finally, no flush
            proc.wait()
        assert len(srv.texts_served) < n                    # killed mid-run
        in_journal = (journal.stat().st_size - 8) // rec
        journaled_keys = set(read_journal(journal)[0])
        journaled_texts = {t for t in texts if text_key("api|stub-bge-m3|None", t) in journaled_keys}
        assert len(journaled_texts) == in_journal
        stored_before = len(EmbeddingStore(tmp_path / "state" / "embeddings", "api|stub-bge-m3|None"))
        assert srv.wait_idle()                              # the dead client's requests finish server-side
        srv.reset_counts()
        capsys.readouterr()
        os.environ["ATLAS_TEST_KEY"] = "dummy"
        try:
            arr = embed(cfg)
        finally:
            del os.environ["ATLAS_TEST_KEY"]
        out = capsys.readouterr().out
        assert f"recovered {in_journal} vectors from journal" in out
        assert len(srv.texts_served) == n - stored_before - in_journal     # only the remaining texts were sent
        assert not set(srv.texts_served) & journaled_texts                 # nothing recovered was paid twice
        final = EmbeddingStore(tmp_path / "state" / "embeddings", "api|stub-bge-m3|None")
        assert len(final) == n and final.index["key"].is_unique
        assert arr.shape[0] == n == np.load(tmp_path / "work" / "03_embeddings.npy").shape[0]
