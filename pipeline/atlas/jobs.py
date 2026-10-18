"""Plumbing for long, resumable jobs (embedding now, LLM runs in P1) — nothing embedding-specific.

Each job owns a folder under state_dir with:
  run.lock       JSON {pid, host, started_at}; created atomically; a dead PID or an old heartbeat = stale
  progress.json  status snapshot, written atomically (heartbeat for the lock and for `atlas status`)
  stop.flag      `atlas embed-stop` creates it; the runner stops cleanly when it sees it
  run.log        stdout+stderr of a --background run
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

LOCK, PROGRESS, STOP, LOG = "run.lock", "progress.json", "stop.flag", "run.log"
ACTIVE = ("running", "backing_off")


class LockHeld(RuntimeError):
    """Another live process holds the job's run.lock."""

    def __init__(self, message: str, pid: int | None):
        super().__init__(message)
        self.pid = pid


class RunStopped(RuntimeError):
    """The run ended early because a stop was requested (Ctrl-C or stop.flag)."""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_iso(value: Any) -> float | None:
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except (TypeError, ValueError):
        return None


def fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    s = int(max(0, round(seconds)))
    if s >= 3600:
        return f"{s // 3600}h {s % 3600 // 60:02d}m"
    if s >= 60:
        return f"{s // 60}m {s % 60:02d}s"
    return f"{s}s"


def pid_alive(pid: Any) -> bool:
    """True when a process with this PID is running. Never signals it (os.kill(pid, 0) kills on Windows)."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        k32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        k32.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = k32.OpenProcess(0x1000, False, pid)            # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.get_last_error() == 5                 # ERROR_ACCESS_DENIED: exists, not ours
        try:
            code = wintypes.DWORD()
            return bool(k32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_json(path: str | Path) -> dict | None:
    """The JSON object in `path`, or None when missing, half-written or locked."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_json_atomic(path: str | Path, obj: dict, *, retries: int = 20, retry_delay: float = 0.05) -> bool:
    """tmp + os.replace, so readers never see half a file. On Windows the replace fails while another
    process has the file open; retry briefly, then skip this write (returns False) — progress is best effort."""
    path = Path(path)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    for attempt in range(retries + 1):
        try:
            os.replace(tmp, path)
            return True
        except PermissionError:
            if attempt < retries:
                time.sleep(retry_delay)
    try:
        tmp.unlink()
    except OSError:
        pass
    return False


class RunLock:
    """Exclusive run.lock with stale takeover (dead PID, or no heartbeat for `stale_seconds`)."""

    def __init__(self, path: str | Path, *, stale_seconds: float = 300, heartbeat: str | Path | None = None,
                 log: Callable[[str], Any] = print):
        self.path, self.stale_seconds = Path(path), float(stale_seconds)
        self.heartbeat = Path(heartbeat) if heartbeat else None
        self.log, self.held = log, False

    def _create(self) -> bool:
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "host": socket.gethostname(), "started_at": now_iso()}, f)
        return True

    def acquire(self) -> RunLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(3):
            if self._create():
                self.held = True
                return self
            state = inspect_lock(self.path, self.heartbeat, self.stale_seconds)
            if not state["exists"]:
                continue                                   # released between our two calls
            if not state["stale"]:
                pid = state["pid"]
                raise LockHeld(f"\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER MAI EK} (PID {pid}) / another run is in progress (PID {pid}) — "
                               f"lock {self.path}", pid)
            self.log(f"[lock] taking over a stale lock ({state['reason']}): {self.path}")
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
        raise LockHeld(f"could not acquire {self.path}", None)

    def release(self) -> None:
        if not self.held:
            return
        self.held = False
        info = read_json(self.path) or {}
        if info.get("pid") == os.getpid() and info.get("host") == socket.gethostname():
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass

    def __enter__(self) -> RunLock:
        return self.acquire()

    def __exit__(self, *exc) -> None:
        self.release()


def inspect_lock(path: Path, heartbeat: Path | None, stale_seconds: float) -> dict:
    """{exists, pid, alive, stale, reason} for a run.lock (heartbeat = progress.json updated_at)."""
    path = Path(path)
    if not path.exists():
        return {"exists": False, "pid": None, "alive": False, "stale": True, "reason": "no lock"}
    info = read_json(path)
    if info is None:
        try:
            young = time.time() - path.stat().st_mtime < 10
        except OSError:
            young = False
        # an empty/corrupt lock that is seconds old is being written right now: treat it as held
        return {"exists": True, "pid": None, "alive": young, "stale": not young, "reason": "unreadable lock file"}
    pid = info.get("pid")
    same_host = info.get("host") in (None, socket.gethostname())
    alive = pid_alive(pid) if same_host else True          # another machine: judge by the heartbeat only
    beats = [parse_iso(info.get("started_at")) or 0.0]
    prog = read_json(heartbeat) if heartbeat else None
    if prog and prog.get("pid") == pid:
        beats.append(parse_iso(prog.get("updated_at")) or 0.0)
    age = time.time() - max(beats)
    if not alive:
        return {"exists": True, "pid": pid, "alive": False, "stale": True, "reason": f"PID {pid} is not running"}
    if age > stale_seconds:
        return {"exists": True, "pid": pid, "alive": alive, "stale": True,
                "reason": f"no heartbeat for {fmt_duration(age)} (lock_stale_seconds={stale_seconds:g})"}
    return {"exists": True, "pid": pid, "alive": True, "stale": False, "reason": ""}


class StopFlag:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def request(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(now_iso(), encoding="utf-8")

    def is_set(self) -> bool:
        return self.path.exists()

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


class ProgressFile:
    """progress.json writer: always on the first write, a status change or force; else every min_interval s."""

    def __init__(self, path: str | Path, min_interval: float = 30.0, clock: Callable[[], float] = time.monotonic):
        self.path, self.min_interval, self.clock = Path(path), float(min_interval), clock
        self._last: float | None = None
        self._last_status: Any = object()

    def write(self, data: dict, force: bool = False) -> bool:
        now = self.clock()
        due = self._last is None or now - self._last >= self.min_interval
        if not (force or due or data.get("status") != self._last_status):
            return False
        if write_json_atomic(self.path, data):
            self._last, self._last_status = now, data.get("status")
            return True
        return False


_SPAWNED: list[subprocess.Popen] = []      # keep handles alive: no ResourceWarning for a child we never wait on


def python_command() -> tuple[str, dict]:
    """(interpreter, env) for a child Python in this environment.

    On Windows a venv's python.exe is a redirector that starts the real interpreter as a second process —
    in a NEW visible console when detached, and under a different PID. Like multiprocessing (bpo-35797) we
    start the base interpreter directly with __PYVENV_LAUNCHER__ so the PID we report is the one that runs.
    """
    exe, env = sys.executable, dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"           # run.log stays UTF-8 even for tracebacks before use_utf8_stdio()
    base =getattr(sys, "_base_executable", exe)
    if os.name == "nt" and base and os.path.normcase(base) != os.path.normcase(exe) and os.path.exists(base):
        env["__PYVENV_LAUNCHER__"] = exe
        exe = base
    return exe, env


def spawn_background(args: list[str], log_path: str | Path, cwd: str | Path | None = None) -> int:
    """Start `python <args>` detached from this console (survives closing the window); stdout+stderr are
    appended to log_path. Returns the child's PID.

    Windows: CREATE_NO_WINDOW (a hidden console of its own, inherited by multiprocessing workers, so no
    window ever pops up) + CREATE_NEW_PROCESS_GROUP, and break away from the parent's job object when allowed.
    POSIX: a new session.
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exe, env = python_command()
    with open(log_path, "ab") as log:
        kw: dict[str, Any] = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": subprocess.STDOUT,
                              "cwd": str(cwd) if cwd else None, "env": env, "close_fds": True}
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            try:
                proc = subprocess.Popen([exe, *args], creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **kw)
            except OSError:                                # the job does not allow breakaway
                proc = subprocess.Popen([exe, *args], creationflags=flags, **kw)
        else:
            proc = subprocess.Popen([exe, *args], start_new_session=True, **kw)
    _SPAWNED.append(proc)
    return proc.pid


# ---------- status (`atlas status`)
_STATUS_TH = {
    "running": "\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}",
    "backing_off": "\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER O ANG} server (backoff)",
    "stopped": "\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA U}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN} — \N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER PHO PHAN}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}",
    "interrupted": "\N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER CHO CHAN}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER SARA A} — \N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER PHO PHAN}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}",
    "done": "\N{THAI CHARACTER SARA E}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAITAIKHU}\N{THAI CHARACTER CHO CHAN}",
    "failed": "\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER WO WAEN} — \N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA UU} last_error",
}


def find_jobs(state_dir: str | Path) -> list[Path]:
    """Every job folder (one holding a progress.json) under state_dir."""
    root = Path(state_dir)
    return sorted(p.parent for p in root.rglob(PROGRESS)) if root.exists() else []


def job_status(job_dir: str | Path, stale_seconds: float = 300) -> dict:
    """progress.json + lock state; a running/backing_off job whose lock is gone or stale is `interrupted`."""
    job_dir = Path(job_dir)
    prog = read_json(job_dir / PROGRESS) or {}
    lock = inspect_lock(job_dir / LOCK, job_dir / PROGRESS, stale_seconds)
    status = prog.get("status", "unknown")
    if status in ACTIVE and (not lock["exists"] or lock["stale"]):
        status = "interrupted"
    return {**prog, "status": status, "recorded_status": prog.get("status"), "dir": str(job_dir),
            "lock_pid": lock["pid"], "lock_alive": lock["alive"] if lock["exists"] else None,
            "stop_requested": (job_dir / STOP).exists()}


def format_job_status(info: dict, extra: list[str] | None = None) -> str:
    """A readable bilingual block for one job."""
    unit = info.get("unit", "docs")
    status = info.get("status", "unknown")
    lines = [f"[{info.get('kind', 'job')}] {info.get('store_id') or info.get('job_id') or info.get('dir')}"]
    pid = info.get("lock_pid") or info.get("pid")
    alive = info.get("lock_alive")
    pid_txt = f" — PID {pid} ({'alive' if alive else 'not running'})" if pid else ""
    lines.append(f"  \N{THAI CHARACTER SO SUA}\N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA A} / status        : {status} ({_STATUS_TH.get(status, '?')}){pid_txt}")
    total, remaining = info.get("total"), info.get("remaining")
    if total is not None:
        done = int(total) - int(remaining or 0)
        pct = 100.0 * done / total if total else 100.0
        lines.append(f"  \N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA} / progress : {done:,} / {int(total):,} {unit} ({pct:.1f}%) · "
                     f"cached {int(info.get('cached') or 0):,} · this run {int(info.get('embedded') or 0):,} · "
                     f"remaining {int(remaining or 0):,}")
    if status in ACTIVE:
        rate = info.get("rate_per_s")
        lines.append(f"  \N{THAI CHARACTER O ANG}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA AA} / rate          : {rate or 0:.1f} {unit}/s · ETA {fmt_duration(info.get('eta_s'))}")
    lines.append(f"  retry / truncated     : {int(info.get('retries') or 0):,} / {int(info.get('truncated') or 0):,}")
    if info.get("last_error"):
        lines.append(f"  error \N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER SARA U}\N{THAI CHARACTER DO DEK} / last error: {info['last_error']} ({info.get('last_error_at', '-')})")
    lines += extra or []
    if info.get("stop_requested"):
        lines.append("  stop.flag             : \N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA U}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN} \N{THAI CHARACTER RO RUA}\N{THAI CHARACTER O ANG} request \N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER CHO CHAN}\N{THAI CHARACTER BO BAIMAI} / stop requested, finishing in-flight work")
    upd = parse_iso(info.get("updated_at"))
    ago = f" ({fmt_duration(time.time() - upd)} ago)" if upd else ""
    lines.append(f"  \N{THAI CHARACTER O ANG}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER TO TAO} / updated       : {info.get('updated_at', '-')}{ago}")
    lines.append(f"  folder                : {info.get('dir')}")
    return "\n".join(lines)
