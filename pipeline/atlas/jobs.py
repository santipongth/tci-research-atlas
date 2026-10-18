"""Plumbing for long, resumable jobs (embedding now, LLM runs in P1) — nothing embedding-specific.

Each job owns a folder under state_dir with:
  .lock          never deleted; the running process holds an OS lock on it (msvcrt / fcntl) for the whole
                 run. The kernel releases it when the process dies, so exclusivity never depends on PIDs
                 or heartbeats.
  run.lock       information only: {pid, host, started_at, pid_started}; read by `atlas status`
  progress.json  status snapshot, written atomically (the heartbeat `atlas status` shows)
  stop.flag      `atlas embed-stop` creates it; the runner stops cleanly when it sees it
  run.log        stdout+stderr of a --background run
"""
from __future__ import annotations

import errno
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from atlas.io_utils import replace_with_retry, unlink_with_retry

LOCK, OSLOCK, PROGRESS, STOP, LOG = "run.lock", ".lock", "progress.json", "stop.flag", "run.log"
ACTIVE = ("running", "backing_off")


class LockHeld(RuntimeError):
    """Another live process holds the job's lock."""

    def __init__(self, message: str, pid: int | None, hung: bool = False):
        super().__init__(message)
        self.pid, self.hung = pid, hung


class RunStopped(RuntimeError):
    """The run ended early because a stop was requested (Ctrl-C or stop.flag)."""

    def __init__(self, message: str = "", abandoned: int = 0):
        super().__init__(message)
        self.abandoned = abandoned          # in-flight requests left behind by a second Ctrl-C


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
    if seconds < 10:
        return f"{max(0.0, seconds):.1f}s"
    s = int(round(seconds))
    if s >= 3600:
        return f"{s // 3600}h {s % 3600 // 60:02d}m"
    if s >= 60:
        return f"{s // 60}m {s % 60:02d}s"
    return f"{s}s"


# ---------- processes
def _kernel32():
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    k32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    k32.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    return k32


def pid_alive(pid: Any) -> bool:
    """True when a process with this PID is running. Never signals it (os.kill(pid, 0) kills on Windows)."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        k32 = _kernel32()
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


def process_start_time(pid: Any) -> int | None:
    """An opaque, exact start stamp of process `pid` (Windows creation FILETIME; Linux start ticks), or None
    when it cannot be read. A PID that was reused by a new process gets a different stamp."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        k32 = _kernel32()
        handle = k32.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            t = [wintypes.FILETIME() for _ in range(4)]
            if not k32.GetProcessTimes(handle, *(ctypes.byref(x) for x in t)):
                return None
            return (t[0].dwHighDateTime << 32) | t[0].dwLowDateTime
        finally:
            k32.CloseHandle(handle)
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        return int(stat.rsplit(")", 1)[1].split()[19])          # field 22: starttime (clock ticks since boot)
    except (OSError, IndexError, ValueError):
        return None


def process_alive(pid: Any, started: Any = None) -> bool:
    """pid_alive, and — when the start stamp was recorded — still the same process (not a reused PID)."""
    if not pid_alive(pid):
        return False
    if started is None:
        return True
    now = process_start_time(pid)
    return now is None or now == started


def process_started_epoch() -> float:
    """When this process started (epoch seconds); a stop.flag written after this belongs to this run."""
    stamp = process_start_time(os.getpid())
    if stamp is not None and os.name == "nt":
        return (stamp - 116_444_736_000_000_000) / 1e7          # FILETIME (100 ns since 1601) -> epoch
    if stamp is not None:
        try:
            btime = next(int(line.split()[1]) for line in Path("/proc/stat").read_text().splitlines()
                         if line.startswith("btime"))
            return btime + stamp / os.sysconf("SC_CLK_TCK")
        except (OSError, StopIteration, ValueError):
            pass
    return _IMPORTED_AT


_IMPORTED_AT = time.time()


# ---------- files
def read_json(path: str | Path | None) -> dict | None:
    """The JSON object in `path`, or None when missing, half-written or locked."""
    if path is None:
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_json_atomic(path: str | Path, obj: dict, *, timeout: float = 1.0) -> bool:
    """tmp + os.replace, so readers never see half a file. On Windows the replace fails while another
    process has the file open: retry for up to `timeout` s, then skip this write (False) — best effort."""
    path = Path(path)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        replace_with_retry(tmp, path, timeout=timeout)
        return True
    except PermissionError:
        unlink_with_retry(tmp, timeout=0.2)
        return False


# ---------- the lock
class LockUnsupported(RuntimeError):
    """The filesystem cannot lock files (some network shares): one-writer-per-store cannot be guaranteed."""


# errnos that mean "another handle holds the lock"; anything else = locking itself does not work here
_HELD_ERRNOS = {errno.EACCES, errno.EAGAIN, getattr(errno, "EWOULDBLOCK", errno.EAGAIN),
                getattr(errno, "EDEADLK", -1), getattr(errno, "EDEADLOCK", -1)}
_HELD_WINERRORS = {33, 36}                                    # ERROR_LOCK_VIOLATION, ERROR_SHARING_BUFFER_EXCEEDED


def _os_lock(fd: int) -> bool:
    """Try to lock byte 0 of `fd` without blocking: True = we hold it, False = someone else does.
    Any other failure raises LockUnsupported."""
    try:
        if os.name == "nt":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)              # byte 0 (beyond EOF is fine on Windows)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        if e.errno in _HELD_ERRNOS or getattr(e, "winerror", None) in _HELD_WINERRORS:
            return False
        raise LockUnsupported(f"\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA A}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER FO FAN}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER THANTHAKHAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAITAIKHU}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER FO FAN}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER THANTHAKHAT}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER MAI THO} ({e}) — \N{THAI CHARACTER YO YAK}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER YO YAK} state_dir \N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER THANTHAKHAT}\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU} / this filesystem "
                              f"does not support file locking ({e}); put state_dir on a local disk") from None
    return True


def _os_unlock(fd: int) -> None:
    try:
        if os.name == "nt":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass
    finally:
        os.close(fd)


def os_lock_held(job_dir: str | Path) -> bool | None:
    """Is a live process holding `<job_dir>/.lock` right now? (A non-blocking try-and-release; a run that is
    starting at that instant retries for RunLock.wait.) False when the folder never held a run; None when
    the filesystem cannot lock."""
    path = Path(job_dir) / OSLOCK
    try:
        fd = os.open(path, os.O_RDWR)
    except FileNotFoundError:
        return False
    except OSError:
        return None
    try:
        got = _os_lock(fd)
    except LockUnsupported:
        os.close(fd)
        return None
    if got:
        _os_unlock(fd)                                          # also closes fd
        return False
    os.close(fd)
    return True


class RunLock:
    """Exclusive lock for one job folder.

    Exclusivity = an OS lock held on `<dir>/.lock` (never deleted) for the life of the run; the kernel drops
    it when the process dies, so a killed run is taken over at once and a live one — even a hung one whose
    heartbeat is old — never is. `run.lock` (JSON: pid, host, started_at, pid_started) is information for
    `atlas status` only. `wait` = how long acquire() retries before raising LockHeld.
    """

    def __init__(self, path: str | Path, *, stale_seconds: float = 300, heartbeat: str | Path | None = None,
                 log: Callable[[str], Any] = print, wait: float = 0.5):
        self.path = Path(path)
        self.os_path = self.path.parent / OSLOCK
        self.stale_seconds, self.wait = float(stale_seconds), float(wait)
        self.heartbeat = Path(heartbeat) if heartbeat else None
        self.log, self.held = log, False
        self._fd: int | None = None

    def _try(self) -> bool:
        fd = os.open(self.os_path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            got = _os_lock(fd)
        except LockUnsupported as e:
            os.close(fd)
            raise LockUnsupported(f"{e} — lock file {self.os_path}") from None
        if got:
            self._fd = fd
            return True
        os.close(fd)
        return False

    def acquire(self) -> RunLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.wait
        while not self._try():
            if time.monotonic() >= deadline:
                st = lock_state(self.path, self.heartbeat, self.stale_seconds)
                pid, age = st["pid"], st["heartbeat_age"]
                hung = age is not None and age > self.stale_seconds        # the holder is alive by definition
                if hung:
                    msg = (f"\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NGO NGU} (hung) — \N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA II} heartbeat \N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU} {fmt_duration(age)} \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK} process \N{THAI CHARACTER YO YAK}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER MAI EK} "
                           f"(PID {pid}) / hung — no heartbeat for {fmt_duration(age)} but the "
                           f"process (PID {pid}) still holds the lock; it is never taken over while it lives — check "
                           f"it, or end it (taskkill /F /PID {pid}) and run again")
                else:
                    msg = f"\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER MAI EK} (PID {pid}) / another run is in progress (PID {pid})"
                raise LockHeld(f"{msg} — lock {self.os_path}", pid, hung=hung)
            time.sleep(0.05)
        try:
            prev = read_json(self.path)
            if prev is not None:
                self.log(f"[lock] previous run (PID {prev.get('pid')}, started {prev.get('started_at')}) ended "
                         f"without releasing run.lock (stale) — taking over: {self.path}")
            info = {"pid": os.getpid(), "host": socket.gethostname(), "started_at": now_iso(),
                    "pid_started": process_start_time(os.getpid())}
            if not write_json_atomic(self.path, info, timeout=10.0):
                self.log(f"[lock] WARNING: could not write {self.path} (information only)")
        except BaseException:
            _os_unlock(self._fd)                                # never leak the OS lock
            self._fd = None
            raise
        self.held = True
        return self

    def release(self) -> None:
        if not self.held:
            return
        self.held = False
        info = read_json(self.path) or {}
        if info.get("pid") == os.getpid() and info.get("host") == socket.gethostname():
            unlink_with_retry(self.path)                       # information only: a leftover is harmless
        if self._fd is not None:
            _os_unlock(self._fd)
            self._fd = None

    def __enter__(self) -> RunLock:
        return self.acquire()

    def __exit__(self, *exc) -> None:
        self.release()


def lock_state(path: str | Path, heartbeat: str | Path | None, stale_seconds: float) -> dict:
    """What run.lock says, without touching the OS lock: {exists, pid, alive, hung, heartbeat_age}.

    alive = the recorded process still runs (same start stamp, so a reused PID does not count). The heartbeat
    is progress.json `updated_at` of that process (else run.lock `started_at`); hung = alive but silent for
    longer than stale_seconds. Another host's PID cannot be checked: there, alive = a recent heartbeat.
    """
    path = Path(path)
    info = read_json(path)
    if info is None:
        return {"exists": path.exists(), "pid": None, "alive": False, "hung": False, "heartbeat_age": None}
    pid = info.get("pid")
    prog = read_json(heartbeat) if heartbeat else None
    beat = parse_iso(prog.get("updated_at")) if prog and prog.get("pid") == pid else None
    beat = beat or parse_iso(info.get("started_at"))
    age = time.time() - beat if beat else None
    if info.get("host") in (None, socket.gethostname()):
        alive = process_alive(pid, info.get("pid_started"))
    else:
        alive = age is not None and age <= stale_seconds
    hung = bool(alive and age is not None and age > stale_seconds)
    return {"exists": True, "pid": pid, "alive": alive, "hung": hung, "heartbeat_age": age}


class StopFlag:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def request(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(now_iso(), encoding="utf-8")

    def is_set(self) -> bool:
        return self.path.exists()

    def clear(self) -> None:
        unlink_with_retry(self.path)

    def clear_if_older(self, epoch: float) -> bool:
        """Remove a flag written before `epoch` (left from an earlier run); True when one was removed."""
        try:
            if self.path.stat().st_mtime < epoch:
                return unlink_with_retry(self.path)
        except FileNotFoundError:
            pass
        return False


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


# ---------- background runs
@dataclass
class Spawned:
    pid: int
    proc: subprocess.Popen
    breakaway: bool                 # Windows: left the parent's job object (cannot be killed with it)
    warning: str | None             # set when the child may die with this terminal


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
    base = getattr(sys, "_base_executable", exe)
    if os.name == "nt" and base and os.path.normcase(base) != os.path.normcase(exe) and os.path.exists(base):
        env["__PYVENV_LAUNCHER__"] = exe
        exe = base
    return exe, env


def kill_on_close_job() -> bool:
    """Windows: True when this process sits in a job object that kills its members when it closes and does
    not let children leave silently — a child that could not break away dies with this terminal/launcher."""
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class Io(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint64) for n in ("r", "w", "o", "rb", "wb", "ob")]

    class Extended(ctypes.Structure):
        _fields_ = [("Basic", Basic), ("Io", Io), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    in_job = wintypes.BOOL()
    if not k32.IsProcessInJob(wintypes.HANDLE(-1), None, ctypes.byref(in_job)) or not in_job.value:
        return False
    info = Extended()
    if not k32.QueryInformationJobObject(None, 9, ctypes.byref(info), ctypes.sizeof(info), None):
        return True                                            # cannot tell: assume the worst
    flags = info.Basic.LimitFlags
    return bool(flags & 0x2000) and not flags & 0x1000         # KILL_ON_JOB_CLOSE, not SILENT_BREAKAWAY_OK


def spawn_background(args: list[str], log_path: str | Path, cwd: str | Path | None = None) -> Spawned:
    """Start `python <args>` detached from this console (survives closing the window); stdout+stderr are
    appended to log_path.

    Windows: CREATE_NO_WINDOW (a hidden console of its own, inherited by multiprocessing workers, so no
    window ever pops up) + CREATE_NEW_PROCESS_GROUP, and break away from the parent's job object when allowed
    (if not, and that job kills its members on close, `warning` says so). POSIX: a new session.
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exe, env = python_command()
    breakaway, warning = False, None
    with open(log_path, "ab") as log:
        kw: dict[str, Any] = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": subprocess.STDOUT,
                              "cwd": str(cwd) if cwd else None, "env": env, "close_fds": True}
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            try:
                proc = subprocess.Popen([exe, *args], creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **kw)
                breakaway = True
            except OSError:                                # the job does not allow breakaway
                proc = subprocess.Popen([exe, *args], creationflags=flags, **kw)
                if kill_on_close_job():
                    warning = ("this terminal runs inside a Windows job that kills its processes when it closes, "
                               "and the background run could not leave it — keep this window open, or start the "
                               "command from a plain PowerShell/cmd window")
        else:
            proc = subprocess.Popen([exe, *args], start_new_session=True, **kw)
            breakaway = True
    _SPAWNED.append(proc)
    return Spawned(proc.pid, proc, breakaway, warning)


# ---------- status (`atlas status`)
_STATUS_TH = {
    "running": "\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}",
    "backing_off": "\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER O ANG} server (backoff)",
    "hung": "\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NGO NGU} — process \N{THAI CHARACTER YO YAK}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA II} heartbeat; \N{THAI CHARACTER TO TAO}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER CHO CHAN}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA UU} \N{THAI CHARACTER HO HIP}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER O ANG} taskkill \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}",
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
    """progress.json + run.lock (information only — the OS lock is never touched here).
    A running/backing_off job whose process is gone is `interrupted`; alive but silent = `hung`."""
    job_dir = Path(job_dir)
    prog = read_json(job_dir / PROGRESS) or {}
    lock = lock_state(job_dir / LOCK, job_dir / PROGRESS, stale_seconds)
    held = os_lock_held(job_dir) if (job_dir / OSLOCK).exists() else None
    alive = held if held is not None else lock["alive"]        # the OS lock decides; run.lock only informs
    age = lock["heartbeat_age"]
    if held and age is None:                                   # run.lock missing: heartbeat from progress.json
        upd = parse_iso(prog.get("updated_at"))
        age = time.time() - upd if upd else None
    hung = bool(alive and age is not None and age > stale_seconds)
    status = prog.get("status", "unknown")
    if status in ACTIVE:
        if not alive:
            status = "interrupted"
        elif hung:
            status = "hung"
    return {**prog, "status": status, "recorded_status": prog.get("status"), "dir": str(job_dir),
            "lock_pid": lock["pid"] or (prog.get("pid") if alive else None),
            "lock_alive": alive if (lock["exists"] or held is not None) else None,
            "heartbeat_age": age, "stop_requested": (job_dir / STOP).exists()}


def format_job_status(info: dict, extra: list[str] | None = None) -> str:
    """A readable bilingual block for one job."""
    unit = info.get("unit", "docs")
    status = info.get("status", "unknown")
    lines = [f"[{info.get('kind', 'job')}] {info.get('store_id') or info.get('job_id') or info.get('dir')}"]
    pid = info.get("lock_pid") or info.get("pid")
    alive = info.get("lock_alive")
    pid_txt = f" — PID {pid} ({'alive' if alive else 'not running'})" if pid else ""
    lines.append(f"  \N{THAI CHARACTER SO SUA}\N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA A} / status        : {status} ({_STATUS_TH.get(status, '?')}){pid_txt}")
    if info.get("checkpoint_postponed"):
        lines.append(f"  checkpoint            : postponed {int(info['checkpoint_postponed'])} times in a row — something "
                     f"holds index.parquet (antivirus/backup?); results are safe in journal.bin")
    if status == "hung":
        lines.append(f"  heartbeat             : none for {fmt_duration(info.get('heartbeat_age'))} "
                     f"(lock_stale_seconds) — the process is alive and keeps the lock")
    total, remaining = info.get("total"), info.get("remaining")
    if not total and status in ACTIVE:
        lines.append("  \N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA} / progress : \N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER MO MA} (\N{THAI CHARACTER O ANG}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU} journal / \N{THAI CHARACTER NO NU}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU}) / starting (journal replay, counting work)")
    elif total is not None:
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
