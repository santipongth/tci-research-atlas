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
from atlas.jobs import LockHeld, RunLock, now_iso, read_json

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
def test_lock_held_by_a_live_run_refuses_to_run(tmp_path):
    store = store_for(tmp_path)
    with RunLock(store.dir / "run.lock"):                                     # another run holds the store
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
    os.utime(store.dir / "stop.flag", (time.time() - 86_400,) * 2)         # written before this process started
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


def test_store_status_lines_word_the_journal_by_run_state(tmp_path):
    from atlas.embed_runner import store_status_lines

    store = store_for(tmp_path)
    store.add(keys_of(TEXTS[:2]), np.stack([fake_vec(t) for t in TEXTS[:2]]))
    _write_journal(store.dir / JOURNAL, keys_of(TEXTS[2:5]), np.stack([fake_vec(t) for t in TEXTS[2:5]]))
    idle = store_status_lines(store.dir)[0]
    live = store_status_lines(store.dir, active=True)[0]
    assert "2 vectors" in idle and "3 vectors waiting" in idle and "next run" in idle
    assert "next checkpoint" in live


# ---------- fix round 1: Windows readers, two-writer defence
def _hold_open(path, seconds):
    """A reader (like `atlas status` or an antivirus) holding `path` open for a while, from another thread."""
    def run():
        for _ in range(400):
            if path.exists():
                break
            time.sleep(0.005)
        with open(path, "rb"):
            time.sleep(seconds)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def test_store_add_survives_a_reader_holding_the_index(tmp_path):
    store = store_for(tmp_path)
    store.add(["a" * 40], np.ones((1, 3), dtype=np.float32))
    t = _hold_open(store.dir / "index.parquet", 0.5)
    time.sleep(0.05)
    store.add(["b" * 40], np.full((1, 3), 2, dtype=np.float32))       # waits for the reader, then replaces
    t.join()
    again = store_for(tmp_path)
    assert len(again) == 2 and np.array_equal(again.get(["b" * 40]), np.full((1, 3), 2, dtype=np.float32))


@pytest.mark.skipif(os.name != "nt", reason="POSIX lets you replace an open file")
def test_store_add_that_cannot_replace_the_index_leaves_no_trace(tmp_path):
    store = store_for(tmp_path)
    store.add(["a" * 40], np.ones((1, 3), dtype=np.float32))
    shards = sorted(p.name for p in store.dir.glob("shard_*.npy"))
    with open(store.dir / "index.parquet", "rb"):
        with pytest.raises(PermissionError):
            store.add(["b" * 40], np.ones((1, 3), dtype=np.float32), replace_timeout=0.3)
    assert sorted(p.name for p in store.dir.glob("shard_*.npy")) == shards   # no orphan shard
    assert len(store) == 1 and not store.has("b" * 40)                        # memory matches disk
    store.add(["b" * 40], np.ones((1, 3), dtype=np.float32))                  # and it works afterwards
    assert len(store_for(tmp_path)) == 2


def test_shard_collision_never_overwrites(tmp_path):
    store = store_for(tmp_path)
    (store.dir / "shard_00000.npy").write_bytes(b"someone else's shard")    # e.g. a second writer
    store.add(["a" * 40], np.ones((1, 3), dtype=np.float32))
    assert (store.dir / "shard_00000.npy").read_bytes() == b"someone else's shard"
    assert int(store.index["shard"].iloc[0]) == 1
    assert np.array_equal(store_for(tmp_path).get(["a" * 40]), np.ones((1, 3), dtype=np.float32))


def test_run_completes_while_a_reader_holds_the_index_across_checkpoints(tmp_path):
    store = store_for(tmp_path)

    class Slowish(Fake):
        def embed_batch(self, texts):
            time.sleep(0.02)
            return super().embed_batch(texts)
    readers = []

    def hook(n):
        if n == 3:                                         # after the first checkpoint created index.parquet
            readers.append(_hold_open(store.dir / "index.parquet", 1.5))
    stats = run_embedding(TEXTS * 1, Slowish(hook=hook), store, rcfg(checkpoint_every=4), progress=False)
    assert stats["status"] == "done" and len(store_for(tmp_path)) == 40
    assert read_json(store.dir / "progress.json")["status"] == "done"


def test_progress_publishes_store_and_journal_counts(tmp_path):
    store = store_for(tmp_path)
    seen = []

    def hook(n):
        if n == 5:
            seen.append(read_json(store.dir / "progress.json"))
    run_embedding(TEXTS, Fake(hook=hook), store, rcfg(checkpoint_every=8), progress=False)
    final = read_json(store.dir / "progress.json")
    assert final["store_vectors"] == 40 and final["journal_pending"] == 0
    assert "store_vectors" in seen[0] and "journal_pending" in seen[0]


def test_stop_requested_before_the_run_reached_embedding_is_honoured(tmp_path):
    store = store_for(tmp_path)
    (store.dir / "stop.flag").write_text("x", encoding="utf-8")      # `embed-stop` while it was still ingesting
    fake = Fake()
    stats = run_embedding(TEXTS, fake, store, rcfg(), progress=False)
    assert stats["status"] == "stopped" and fake.calls == 0
    assert not (store.dir / "stop.flag").exists()


def _api_cfg(**kw):
    return {"embedding": {"api": {"base_url": "http://x/v1", "api_key_env": "NOPE_KEY", "model": "m",
                                  "dimensions": None, "store_id": None, "request_timeout": 5.0, "min_text_chars": 10,
                                  "backoff_initial": 0.01, "backoff_max": 0.02, "max_retries": None,
                                  "requests_per_minute": None, **kw}}}


def _vec_transport(dim=6, max_inputs=None, max_chars=None, after=None):
    """OpenAI-compatible fake: 413 above max_inputs, 400 'maximum context' above max_chars, then `after`."""
    calls = {"n": 0}

    def t(url, headers, body, timeout):
        inp = json.loads(body)["input"]
        calls["n"] += 1
        if max_inputs and len(inp) > max_inputs:
            return 413, {}, b"too large"
        if max_chars and any(len(x) > max_chars for x in inp):
            return 400, {}, b"This model's maximum context length is 8192 tokens"
        if after is not None:
            r = after(calls["n"], inp)
            if r is not None:
                return r
        data = [{"index": i, "embedding": fake_vec(x, dim).tolist()} for i, x in enumerate(inp)]
        return 200, {}, json.dumps({"data": data}).encode()
    return t


def test_split_batch_stopped_half_way_keeps_the_paid_half(tmp_path):
    # batch of 4 -> 413 -> left half paid -> right half hits a dead server -> stop: the left half must be stored
    down = lambda n, inp: (503, {}, b"down") if n > 2 else None          # noqa: E731
    emb = ApiEmbedder(_api_cfg(backoff_initial=60.0, backoff_max=60.0),
                      transport=_vec_transport(max_inputs=2, after=down))
    store = store_for(tmp_path, emb.model_id)
    threading.Timer(0.5, lambda: (store.dir / "stop.flag").write_text("x", encoding="utf-8")).start()
    stats = run_embedding(TEXTS[:4], emb, store, rcfg(batch_size=4, concurrency=1), progress=False)
    assert stats["status"] == "stopped" and stats["embedded"] == 2
    again = store_for(tmp_path, emb.model_id)
    assert len(again) == 2 and np.array_equal(again.get(keys_of(TEXTS[:2], emb.model_id)),
                                              np.stack([fake_vec(t) for t in TEXTS[:2]]))


def test_truncated_texts_are_recorded_and_counted(tmp_path):
    from atlas.embed_runner import TRUNCATED, store_status_lines
    from atlas.io_utils import read_table

    emb = ApiEmbedder(_api_cfg(min_text_chars=50), transport=_vec_transport(max_chars=400))
    store = store_for(tmp_path, emb.model_id)
    texts = TEXTS[:6] + ["L" * 1000, "M" * 2000]
    stats = run_embedding(texts, emb, store, rcfg(), progress=False)
    assert stats["truncated"] == 2
    df = read_table(store.dir / TRUNCATED)
    assert list(df.columns) == ["key", "original_chars", "used_chars", "run_started_at"]
    assert sorted(df["original_chars"]) == [1000, 2000] and sorted(df["used_chars"]) == [250, 250]
    assert set(df["key"]) == set(keys_of(["L" * 1000, "M" * 2000], emb.model_id))
    assert read_json(store.dir / "progress.json")["truncated_total"] == 2
    emb2 = ApiEmbedder(_api_cfg(min_text_chars=50), transport=_vec_transport(max_chars=400))
    run_embedding(texts + ["N" * 900], emb2, store_for(tmp_path, emb.model_id), rcfg(), progress=False)
    assert len(read_table(store.dir / TRUNCATED)) == 3                    # appended per run, cumulative
    assert any("3 in total" in x for x in store_status_lines(store.dir))


def test_second_ctrl_c_abandons_in_flight_requests_at_once(tmp_path):
    release = threading.Event()
    store = store_for(tmp_path)

    def twice():
        _thread.interrupt_main()
        time.sleep(0.8)
        _thread.interrupt_main()

    def hook(n):
        if n == 2:
            threading.Thread(target=twice, daemon=True).start()
        if n >= 2:
            release.wait(30)                               # a slow request that would block for 30 s
    t0 = time.monotonic()
    try:
        stats = run_embedding(TEXTS, Fake(hook=hook), store, rcfg(concurrency=2, checkpoint_every=1000),
                              progress=False)
    finally:
        release.set()
    assert time.monotonic() - t0 < 10
    assert stats["status"] == "stopped" and stats["abandoned"] >= 1
    assert len(store_for(tmp_path)) == stats["embedded"]


# ---------- fix round 2
def test_two_ctrl_c_during_a_slow_checkpoint_still_cancel_and_stop(tmp_path, monkeypatch, capsys):
    # both presses are counted while the main thread is busy in a checkpoint: the loop jumps 0 -> 2
    import atlas.embed_store as es

    calls = {"n": 0}
    lock = threading.Lock()

    def transport(url, headers, body, timeout):
        inp = json.loads(body)["input"]
        with lock:
            calls["n"] += 1
            n = calls["n"]
        if n <= 2:
            return 200, {}, json.dumps({"data": [{"index": i, "embedding": fake_vec(x).tolist()}
                                                 for i, x in enumerate(inp)]}).encode()
        time.sleep(0.05)
        return 503, {}, b"down"                           # then the server is down: retry forever

    orig_add, fired = es.EmbeddingStore.add, []

    def slow_add(self, keys, vectors, **kw):
        if not fired:
            fired.append(1)

            def twice():
                time.sleep(0.2)
                _thread.interrupt_main()
                time.sleep(0.4)
                _thread.interrupt_main()
            threading.Thread(target=twice, daemon=True).start()
            for _ in range(30):                            # a slow checkpoint (short sleeps, so each
                time.sleep(0.05)                           # Ctrl-C is handled while it lasts)
        return orig_add(self, keys, vectors, **kw)
    monkeypatch.setattr(es.EmbeddingStore, "add", slow_add)
    emb = ApiEmbedder(_api_cfg(backoff_initial=0.2, backoff_max=0.4), transport=transport)
    store = store_for(tmp_path, emb.model_id)
    try:
        stats = run_embedding(TEXTS, emb, store, rcfg(batch_size=5, concurrency=2, checkpoint_every=10),
                              progress=False)
        cancelled = emb.policy.cancelled
        time.sleep(1.0)                                    # workers finish their current wait and give up
        c0 = calls["n"]
        time.sleep(1.5)
        c1 = calls["n"]
    finally:
        emb.cancel()                                       # never leave retrying workers behind (hangs pytest)
    assert stats["status"] == "stopped" and stats["abandoned"] >= 0 and cancelled
    assert read_json(store.dir / "progress.json")["status"] == "stopped"
    assert c1 == c0                                        # nobody keeps retrying after the run returned
    out = capsys.readouterr().out
    assert "Ctrl-C again to abandon" not in out             # the jump goes straight to "abandoning"


def test_store_index_is_reloaded_after_taking_the_lock(tmp_path):
    # B opens the store, then A checkpoints and releases while B waits for the lock: B must not re-pay
    store_b = store_for(tmp_path)
    lock_a = RunLock(store_b.dir / "run.lock", log=lambda m: None).acquire()
    store_for(tmp_path).add(keys_of(TEXTS[:20]), np.stack([fake_vec(t) for t in TEXTS[:20]]))
    threading.Timer(0.2, lock_a.release).start()
    fake = Fake()
    stats = run_embedding(TEXTS, fake, store_b, rcfg(), progress=False)
    assert stats["cached"] == 20 and len(fake.texts) == 20
    again = store_for(tmp_path)
    shards = {int(p.stem.split("_")[1]) for p in again.dir.glob("shard_*.npy")}
    assert len(again) == 40 and shards == set(int(x) for x in again.index["shard"].unique())   # no orphan


def test_store_add_removes_its_shard_when_writing_the_index_fails(tmp_path, monkeypatch):
    import atlas.embed_store as es

    store = store_for(tmp_path)
    store.add(["a" * 40], np.ones((1, 3), dtype=np.float32))

    def broken(df, path):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(es, "write_table", broken)
    with pytest.raises(OSError):
        store.add(["b" * 40], np.ones((1, 3), dtype=np.float32))
    assert sorted(p.name for p in store.dir.glob("shard_*.npy")) == ["shard_00000.npy"]
    assert len(store) == 1


@pytest.mark.skipif(os.name != "nt", reason="only Windows blocks replacing a file that is open")
def test_final_flush_failure_keeps_the_journal_and_says_so(tmp_path, monkeypatch):
    import atlas.embed_runner as er
    from atlas.embed_runner import StoreBusy

    monkeypatch.setattr(er, "CHECKPOINT_REPLACE_S", 0.2)
    monkeypatch.setattr(er, "FINAL_REPLACE_S", 0.3)
    store = store_for(tmp_path)
    store.add(keys_of(TEXTS[:1]), fake_vec(TEXTS[0])[None])
    f = open(store.dir / "index.parquet", "rb")                # held for the whole run
    try:
        with pytest.raises(StoreBusy) as e:
            run_embedding(TEXTS, Fake(), store, rcfg(checkpoint_every=1000), progress=False)
        assert "journal" in str(e.value)
        prog = read_json(store.dir / "progress.json")
        assert prog["status"] == "failed" and "journal" in prog["last_error"]
        assert (store.dir / JOURNAL).exists()
    finally:
        f.close()
    again = Fake()
    stats = run_embedding(TEXTS, again, store_for(tmp_path), rcfg(), progress=False)
    assert stats["recovered"] == 39 and again.calls == 0 and len(store_for(tmp_path)) == 40


def _share_rwd_open(path):
    """A reader that allows read|write|delete sharing (as many antivirus/backup agents do)."""
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                wintypes.DWORD, wintypes.HANDLE)
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    h = k32.CreateFileW(str(path), 0x80000000, 0x7, None, 3, 0x80, None)

    class Holder:
        def close(self):
            k32.CloseHandle(h)
    return Holder()


@pytest.mark.skipif(os.name != "nt", reason="only Windows blocks replacing a file that is open")
@pytest.mark.parametrize("holder", ["plain", "share_rwd"])
def test_a_persistent_holder_does_not_cause_repeated_shard_rewrites(tmp_path, monkeypatch, holder):
    import atlas.embed_runner as er
    import atlas.embed_store as es

    monkeypatch.setattr(er, "CHECKPOINT_REPLACE_S", 0.1)
    adds = []
    orig_add = es.EmbeddingStore.add

    def counting_add(self, keys, vectors, **kw):
        adds.append(len(keys))
        return orig_add(self, keys, vectors, **kw)
    monkeypatch.setattr(es.EmbeddingStore, "add", counting_add)
    store = store_for(tmp_path)
    store.add(keys_of(TEXTS[:1]), fake_vec(TEXTS[0])[None])
    adds.clear()
    released, seen, held_adds = threading.Event(), [], []
    f = open(store.dir / "index.parquet", "rb") if holder == "plain" else _share_rwd_open(store.dir / "index.parquet")

    def hook(n):
        if n == 30:                                        # long after 3 postponements
            seen.append(read_json(store.dir / "progress.json"))
            held_adds.append(len(adds))                    # store.add attempts while the file was held
            f.close()
            released.set()
    texts = [f"text {i}" for i in range(200)]
    try:
        stats = run_embedding(texts, Fake(hook=hook), store, rcfg(batch_size=4, checkpoint_every=4), progress=False)
    finally:
        if not released.is_set():
            f.close()
    assert stats["status"] == "done" and len(store_for(tmp_path)) == 201      # + the pre-seeded vector
    assert seen and seen[0]["checkpoint_postponed"] >= 10   # ~30 checkpoints were due while it was held ...
    assert held_adds[0] <= 4                                # ... but only the first 3 rewrote a shard + index


def test_runner_messages_never_break_on_a_cp1252_console(tmp_path, monkeypatch):
    import io

    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="cp1252"))   # a library caller's console
    store = store_for(tmp_path)

    def hook(n):
        if n == 2:
            (store.dir / "stop.flag").write_text("x", encoding="utf-8")   # triggers the Thai stop messages
    stats = run_embedding(TEXTS, Fake(hook=hook), store, rcfg(checkpoint_every=1000), progress=False)
    sys.stdout.flush()
    assert stats["status"] == "stopped" and b"stopping (stop.flag)" in raw.getvalue()



def test_any_final_save_failure_is_typed_and_keeps_the_journal(tmp_path, monkeypatch):
    import errno

    import atlas.embed_store as es
    from atlas.embed_runner import StoreSaveFailed

    store = store_for(tmp_path)

    def disk_full(self, keys, vectors, **kw):
        raise OSError(errno.ENOSPC, "No space left on device")
    monkeypatch.setattr(es.EmbeddingStore, "add", disk_full)
    with pytest.raises(StoreSaveFailed) as e:
        run_embedding(TEXTS, Fake(), store, rcfg(checkpoint_every=1000), progress=False)
    assert "journal.bin" in str(e.value) and "No space left" in str(e.value)
    prog = read_json(store.dir / "progress.json")
    assert prog["status"] == "failed" and "journal.bin" in prog["last_error"]
    monkeypatch.undo()
    again = Fake()
    stats = run_embedding(TEXTS, again, store_for(tmp_path), rcfg(), progress=False)
    assert stats["recovered"] == 40 and again.calls == 0              # nothing paid twice
