"""Embedding runner: batches -> worker threads -> journal -> EmbeddingStore, with lock, stop flag, progress.

Durability (nothing paid for is lost, nothing is paid for twice):
  * every completed batch is appended to <store>/journal.bin at once (flush per batch, fsync <= every 10 s)
  * every `checkpoint_every` vectors the buffer goes into the store (shard + index) and the journal is emptied
  * a new run first replays journal.bin into the store, then embeds only keys the store does not have
  * so a killed process (closed window, crash, power loss) loses at most the requests still in flight

Only the main thread touches the store, the journal and progress.json; workers only call embed_batch.
Retries/backoff live in the embedder (ApiEmbedder); the runner just keeps going and reports.
"""
from __future__ import annotations

import os
import re
import signal
import struct
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, CancelledError, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from atlas.api_http import Cancelled
from atlas.embed_api import dim_mismatch
from atlas.embed_store import EmbeddingStore, text_key
from atlas.jobs import LOCK, PROGRESS, STOP, ProgressFile, RunLock, StopFlag, fmt_duration, now_iso

JOURNAL = "journal.bin"
MAGIC = b"ATJ1"
HEADER = len(MAGIC) + 4
KEY_BYTES = 40                                   # sha1 hex
_HEX = re.compile(rb"[0-9a-f]{40}")
FSYNC_EVERY_S = 10.0
PROGRESS_EVERY_S = 5.0                           # progress.json heartbeat (spec: at least every 30 s)


# ---------- journal
class Journal:
    """Write-ahead log of paid vectors: b"ATJ1" + uint32 dim, then records of 40 ASCII key bytes +
    dim float32 little-endian. Append + flush per batch; os.fsync at most every FSYNC_EVERY_S seconds."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.f = None
        self.dim: int | None = None
        self._synced = time.monotonic()

    def append(self, keys: list[str], vectors: np.ndarray) -> None:
        vectors = np.ascontiguousarray(vectors, dtype="<f4")
        if self.f is None:
            self.dim = int(vectors.shape[1])
            self.f = open(self.path, "wb")                    # any old journal was replayed and deleted at start
            self.f.write(MAGIC + struct.pack("<I", self.dim))
        self.f.write(b"".join(k.encode("ascii") + vectors[i].tobytes() for i, k in enumerate(keys)))
        self.f.flush()
        if time.monotonic() - self._synced >= FSYNC_EVERY_S:
            os.fsync(self.f.fileno())
            self._synced = time.monotonic()

    def truncate(self) -> None:
        """Everything journaled is now durable in the store."""
        if self.f is not None:
            self.f.seek(HEADER)
            self.f.truncate()
            self.f.flush()

    def close(self, delete: bool) -> None:
        if self.f is not None:
            self.f.close()
            self.f = None
        if delete:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass


def read_journal(path: str | Path) -> tuple[list[str], np.ndarray, int]:
    """(keys, vectors, n_skipped): complete, valid records only — a torn tail or zero-filled/garbled
    records (power loss) are skipped."""
    raw = Path(path).read_bytes()
    if len(raw) < HEADER or raw[:4] != MAGIC:
        return [], np.empty((0, 0), dtype=np.float32), 0
    dim = struct.unpack("<I", raw[4:HEADER])[0]
    rec = KEY_BYTES + 4 * dim
    n = (len(raw) - HEADER) // rec
    keys: list[str] = []
    rows: list[np.ndarray] = []
    bad = 0
    for i in range(n):
        off = HEADER + i * rec
        key = raw[off:off + KEY_BYTES]
        vec = np.frombuffer(raw, dtype="<f4", count=dim, offset=off + KEY_BYTES)
        if not _HEX.fullmatch(key) or not np.isfinite(vec).all():
            bad += 1
            continue
        keys.append(key.decode("ascii"))
        rows.append(vec)
    if (len(raw) - HEADER) % rec:
        bad += 1                                                      # the torn record at the end
    arr = np.vstack(rows).astype(np.float32) if rows else np.empty((0, dim), dtype=np.float32)
    return keys, arr, bad


def journal_records(path: str | Path) -> int:
    """Complete records waiting in a journal (recovered by the next run), without reading them."""
    try:
        with open(path, "rb") as f:
            head = f.read(HEADER)
            size = os.fstat(f.fileno()).st_size
    except OSError:
        return 0
    if len(head) < HEADER or head[:4] != MAGIC:
        return 0
    return (size - HEADER) // (KEY_BYTES + 4 * struct.unpack("<I", head[4:])[0])


def store_status_lines(sdir: str | Path, active: bool = False) -> list[str]:
    """Extra `atlas status` lines for an embedding store folder (`active`: a live run owns the journal)."""
    from atlas.io_utils import read_table

    try:
        n = len(read_table(Path(sdir) / "index.parquet"))
    except (FileNotFoundError, OSError, ValueError):
        n = 0
    pending = journal_records(Path(sdir) / JOURNAL)
    line = f"  store                 : {n:,} vectors"
    if pending:
        line += (f" · journal.bin: {pending:,} vectors (go into the store at the next checkpoint)" if active
                 else f" · journal.bin: {pending:,} vectors waiting (the next run recovers them)")
    return [line]


def recover_journal(store: EmbeddingStore, log=print) -> int:
    """Replay <store>/journal.bin into the store, then delete it. Returns the number of vectors recovered."""
    path = store.dir / JOURNAL
    if not path.exists():
        return 0
    keys, vecs, bad = read_journal(path)
    if keys:
        if store.dim is not None and vecs.shape[1] != store.dim:
            raise dim_mismatch(store.dim, int(vecs.shape[1]), "journal")
        store.add(keys, vecs)
    path.unlink()
    log(f"[embed] recovered {len(keys):,} vectors from journal" + (f" ({bad} damaged record(s) skipped)"
                                                                   if bad else ""))
    return len(keys)


def pack_batches(lengths: list[int], batch_size: int, max_chars: int | None) -> list[tuple[int, int]]:
    """Contiguous (start, end) ranges, in order, of at most batch_size texts and max_chars characters;
    a single text longer than max_chars gets a batch of its own."""
    out: list[tuple[int, int]] = []
    start, chars = 0, 0
    for i, n in enumerate(lengths):
        if i > start and (i - start >= batch_size or (max_chars and chars + n > max_chars)):
            out.append((start, i))
            start, chars = i, 0
        chars += n
    if start < len(lengths):
        out.append((start, len(lengths)))
    return out


# ---------- the run
def run_embedding(texts: list[str], embedder, store: EmbeddingStore, rcfg: dict, *, progress: bool = True) -> dict:
    """Embed every text whose key is not in `store`. Returns {total, cached, embedded, retries, truncated,
    status, recovered, store_id}; status is "done" or "stopped" (Ctrl-C / stop.flag). Errors are re-raised
    after everything already paid for is flushed. Raises jobs.LockHeld when another live run holds the lock."""
    lock = RunLock(store.dir / LOCK, stale_seconds=float(rcfg.get("lock_stale_seconds") or 300),
                   heartbeat=store.dir / PROGRESS)
    lock.acquire()
    try:
        return _Run(texts, embedder, store, rcfg, progress).run()
    finally:
        lock.release()


class _Run:
    def __init__(self, texts, embedder, store: EmbeddingStore, rcfg: dict, progress: bool):
        self.texts, self.embedder, self.store = texts, embedder, store
        self.store_id = embedder.model_id
        self.batch_size = max(1, int(rcfg.get("batch_size") or 32))
        self.max_chars = rcfg.get("max_batch_chars")
        self.concurrency = max(1, int(rcfg.get("concurrency") or 1))
        self.checkpoint_every = max(1, int(rcfg.get("checkpoint_every") or 2000))
        self.show = progress
        self.stop_flag = StopFlag(store.dir / STOP)
        self.pf = ProgressFile(store.dir / PROGRESS, min_interval=PROGRESS_EVERY_S)
        self.journal = Journal(store.dir / JOURNAL)
        self.started_at = now_iso()
        self.total = self.cached = self.embedded = self.recovered = 0
        self.remaining = 0
        self.dim: int | None = None
        self.buffer: list[tuple[list[str], np.ndarray]] = []
        self.buffered = 0
        self.in_flight: dict[Future, list[str]] = {}
        self.interrupts = 0
        self.stopping: str | None = None          # why we stopped submitting: "stop.flag" | "Ctrl-C" | "error"
        self.error: BaseException | None = None
        self.final: str | None = None
        self.t_embed = time.monotonic()
        self.pbar = None
        # written by worker threads through on_event
        self._ev = threading.Lock()
        self.last_error: str | None = None
        self.last_error_at: str | None = None
        self.last_event = ""
        self.backoff_until = 0.0
        self.last_retry_at = 0.0
        self.last_ok_at = 0.0
        self._shown_event = ""
        self._shown_at = 0.0

    # ---- events from worker threads
    def on_event(self, kind: str, info: dict) -> None:
        now = time.monotonic()
        with self._ev:
            if kind == "retry":
                self.backoff_until = max(self.backoff_until, now + float(info.get("delay") or 0))
                self.last_retry_at = now
                self.last_error, self.last_error_at = info.get("error"), now_iso()
                self.last_event = (f"{info.get('status') or 'net'} \N{THAI CHARACTER LO LING}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK} #{info.get('attempt')} "
                                   f"\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER NO NU} {fmt_duration(info.get('delay'))}")
            elif kind == "truncated":
                self.last_event = f"\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER O ANG} {info.get('chars')} \N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SO RUSI}\N{THAI CHARACTER RO RUA}"
            elif kind == "split":
                self.last_event = f"\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NGO NGU} batch {info.get('size')} \N{THAI CHARACTER SARA E}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU}"

    def status(self) -> str:
        if self.final:
            return self.final
        with self._ev:
            if time.monotonic() < self.backoff_until and self.last_retry_at > self.last_ok_at:
                return "backing_off"
        return "running"

    def snapshot(self) -> dict:
        elapsed = max(time.monotonic() - self.t_embed, 1e-6)
        rate = self.embedded / elapsed if self.embedded else 0.0
        with self._ev:
            last_error, last_error_at, last_event = self.last_error, self.last_error_at, self.last_event
        return {"kind": "embedding", "unit": "docs", "store_id": self.store_id, "status": self.status(),
                "pid": os.getpid(), "total": self.total, "cached": self.cached, "embedded": self.embedded,
                "remaining": max(0, self.remaining - self.embedded), "rate_per_s": round(rate, 2),
                "eta_s": round((self.remaining - self.embedded) / rate) if rate else None,
                "retries": int(getattr(self.embedder, "n_retries", 0)),
                "truncated": int(getattr(self.embedder, "n_truncated", 0)),
                "last_error": last_error, "last_error_at": last_error_at, "last_event": last_event,
                "recovered": self.recovered, "concurrency": self.concurrency, "in_flight": len(self.in_flight),
                "started_at": self.started_at, "updated_at": now_iso()}

    def tick(self, force: bool = False) -> None:
        snap = self.snapshot()
        self.pf.write(snap, force=force)
        if self.pbar is not None and not self.pbar.disable:
            now = time.monotonic()
            event = snap["last_event"]
            if event != self._shown_event and now - self._shown_at >= self.pbar.mininterval:
                self.pbar.set_postfix(retries=snap["retries"], truncated=snap["truncated"], last=event or "-",
                                      refresh=True)
                self._shown_event, self._shown_at = event, now

    # ---- main-thread bookkeeping
    def accept(self, keys: list[str], vec: Any) -> None:
        vec = np.asarray(vec, dtype=np.float32)
        if vec.ndim != 2 or vec.shape[0] != len(keys):
            raise RuntimeError(f"embedder returned shape {vec.shape} for {len(keys)} texts")
        if self.dim is None:
            self.dim = self.store.dim or int(vec.shape[1])
        if vec.shape[1] != self.dim:
            raise dim_mismatch(self.dim, int(vec.shape[1]), self.store_id)
        self.journal.append(keys, vec)                        # durable first ...
        self.buffer.append((keys, vec))                       # ... then buffered (one atomic list append)
        self.buffered += len(keys)
        self.embedded += len(keys)
        with self._ev:
            self.last_ok_at = time.monotonic()
        if self.pbar is not None:
            self.pbar.update(len(keys))
        if self.buffered >= self.checkpoint_every:
            self.flush()

    def flush(self) -> None:
        if self.buffer:
            keys = [k for ks, _ in self.buffer for k in ks]
            self.store.add(keys, np.vstack([v for _, v in self.buffer]))
            self.buffer, self.buffered = [], 0
        self.journal.truncate()
        self.tick(force=True)

    def begin_stop(self, why: str) -> None:
        if self.stopping:
            return
        self.stopping = why
        for f in self.in_flight:
            f.cancel()                                        # queued batches never start (not paid)
        cancel = getattr(self.embedder, "cancel", None)
        if cancel:
            cancel()                                          # workers in a backoff wait give up at once
        running = sum(1 for f in self.in_flight if not f.done())
        if why != "error":
            print(f"[embed] \N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA U}\N{THAI CHARACTER DO DEK} ({why}): \N{THAI CHARACTER RO RUA}\N{THAI CHARACTER O ANG} request \N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NGO NGU} {running} \N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER RO RUA} / stopping ({why}): waiting for "
                  f"{running} in-flight request(s) — Ctrl-C again to abandon them", flush=True)

    def collect(self, fut: Future, keys: list[str]) -> None:
        try:
            vec = fut.result()
        except (Cancelled, CancelledError):
            return
        except Exception as e:  # noqa: BLE001 — keep what was paid for, then re-raise the first error
            if self.error is None:
                self.error = e
                self.begin_stop("error")
            return
        try:
            self.accept(keys, vec)
        except Exception as e:  # noqa: BLE001
            if self.error is None:
                self.error = e
                self.begin_stop("error")

    # ---- driver
    def run(self) -> dict:
        # Ctrl-C only sets a flag while we run (a KeyboardInterrupt could land between "batch done" and
        # "batch stored" and drop a paid batch); possible in the main thread only.
        try:
            prev_sigint = signal.signal(signal.SIGINT, self._on_sigint)
        except ValueError:
            prev_sigint = None
        try:
            return self._run()
        finally:
            if prev_sigint is not None:
                signal.signal(signal.SIGINT, prev_sigint)

    def _run(self) -> dict:
        self.stop_flag.clear()                                # a stale stop.flag from an earlier run
        self.tick(force=True)                                 # heartbeat before the (possibly long) setup
        self.recovered = recover_journal(self.store)
        keys = [text_key(self.store_id, t) for t in self.texts]
        text_of: dict[str, str] = {}
        for k, t in zip(keys, self.texts):
            text_of.setdefault(k, t)
        todo = [k for k in text_of if not self.store.has(k)]
        self.total, self.cached, self.remaining = len(text_of), len(text_of) - len(todo), len(todo)
        print(f"[embed] {self.cached:,} cached, {len(todo):,} to embed ({self.store_id})", flush=True)
        self.tick(force=True)                                 # totals known: `atlas status` shows them now
        batches = pack_batches([len(text_of[k]) for k in todo], self.batch_size, self.max_chars)
        hooked = hasattr(self.embedder, "on_event")          # ApiEmbedder reports retries/splits/truncation
        prev_handler = self.embedder.on_event if hooked else None
        if hooked:
            self.embedder.on_event = (self.on_event if prev_handler is None
                                      else lambda k, i: (prev_handler(k, i), self.on_event(k, i)))
        tty = bool(getattr(sys.stderr, "isatty", lambda: False)())
        self.pbar = tqdm(total=len(todo), initial=0, desc="embed", unit="doc", disable=not (self.show and todo),
                         mininterval=0.5 if tty else 30.0, dynamic_ncols=True) if todo else None
        self.t_embed = time.monotonic()
        try:
            if todo:
                self.loop(todo, text_of, batches)
        except BaseException as e:                            # unexpected: still flush, end as "failed"
            if self.error is None:
                self.error = e
        finally:
            if hooked:
                self.embedder.on_event = prev_handler
            if self.pbar is not None:
                self._shown_event, self._shown_at = None, 0.0  # final counters on the bar
                self.tick()
                self.pbar.close()
            self.finish()
        if self.error is not None:
            raise self.error
        return {"total": self.total, "cached": self.cached, "embedded": self.embedded,
                "retries": int(getattr(self.embedder, "n_retries", 0)),
                "truncated": int(getattr(self.embedder, "n_truncated", 0)),
                "status": self.final, "recovered": self.recovered, "store_id": self.store_id}

    def _on_sigint(self, signum, frame) -> None:
        self.interrupts += 1                                  # handled by the loop: never raises mid-bookkeeping

    def loop(self, todo: list[str], text_of: dict[str, str], batches: list[tuple[int, int]]) -> None:
        ex = ThreadPoolExecutor(max_workers=self.concurrency, thread_name_prefix="embed")
        pending = iter(batches)
        try:
            while True:
                if self.interrupts >= 2:
                    print(f"[embed] abandoning {len(self.in_flight)} in-flight request(s); their texts are sent "
                          f"again by the next run", flush=True)
                    break
                if self.interrupts and not self.stopping:
                    self.begin_stop("Ctrl-C")
                if not self.stopping and self.stop_flag.is_set():
                    self.begin_stop("stop.flag")
                while not self.stopping and len(self.in_flight) < 2 * self.concurrency:
                    b = next(pending, None)
                    if b is None:
                        break
                    ks = todo[b[0]:b[1]]
                    self.in_flight[ex.submit(self.embedder.embed_batch, [text_of[k] for k in ks])] = ks
                if not self.in_flight:
                    break
                done, _ = wait(list(self.in_flight), timeout=0.5, return_when=FIRST_COMPLETED)
                for fut in done:
                    self.collect(fut, self.in_flight.pop(fut))
                self.tick()
        finally:
            ex.shutdown(wait=False, cancel_futures=True)

    def finish(self) -> None:
        """Flush everything paid for; the journal is deleted only once the store holds it."""
        try:
            self.flush()
        except BaseException:
            self.journal.close(delete=False)                 # keep journal.bin: the next run replays it
            self.final = "failed"
            self.tick(force=True)
            raise
        self.journal.close(delete=True)
        left = self.remaining - self.embedded
        if self.error is not None:
            self.final = "failed"
            with self._ev:                                   # the error that ended the run
                self.last_error = f"{type(self.error).__name__}: {self.error}"
                self.last_error_at = now_iso()
        elif left <= 0:
            self.final = "done"
        else:
            self.final = "stopped" if self.stopping else "failed"
        if self.stopping and self.stopping != "error":
            self.stop_flag.clear()
        self.tick(force=True)
        if self.final == "stopped":
            print(f"[embed] \N{THAI CHARACTER HO HIP}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA U}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN} — \N{THAI CHARACTER SARA E}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAITAIKHU}\N{THAI CHARACTER BO BAIMAI} {self.embedded:,} \N{THAI CHARACTER SARA E}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER NGO NGU} store; \N{THAI CHARACTER SARA E}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER O ANG} {left:,} \N{THAI CHARACTER SARA E}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU} — "
                  f"\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER PHO PHAN}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG} / stopped: {self.embedded:,} vectors of this run are in the store, "
                  f"{left:,} left — run the same command again to resume", flush=True)
