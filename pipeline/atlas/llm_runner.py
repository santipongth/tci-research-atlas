"""LLM job runner — every topic-level LLM call (labels, merge checks, narratives, brief) goes through here.

  cache = journal  state_dir/llm_cache/<task>.jsonl — one JSON line appended and flushed per finished call,
                   keyed by sha256(model + prompt version + rendered prompt). Re-runs and the next quarter never
                   pay twice; a killed process loses only the calls in flight.
  structure        reply → extract_json → the job's pydantic schema; invalid → up to llm.max_repairs repair
                   turns; a failed content check (e.g. narrative grounding) → up to llm.max_regenerations fresh
                   calls; still failing → the item's fallback (never cached). Transient errors outlasting an
                   endpoint's max_retries (only when it is set) → the fallback too; the next run asks again.
  stopping         permanent endpoint errors (key / model / URL / quota) raise LlmConfigError at once (CLI exit
                   2). `atlas llm-stop` (stop.flag), Ctrl-C and llm.budget_usd (per release, all tasks) end the job
                   after the calls in flight and raise jobs.RunStopped: the step writes nothing, the CLI exits
                   130, and the same command continues (finished calls come from the cache, free).
  P0 plumbing      atlas.jobs exactly as the embedding runner uses it: one LLM job at a time (RunLock = OS lock
                   on state_dir/llm_cache/.lock), StopFlag, and a ProgressFile heartbeat (progress.json, kind
                   "llm") that `atlas status` lists next to the embedding stores.

Jobs register in JOBS ("task" → "module:function" returning an LlmJob for the current work_dir) so
`atlas llm --dry-run` can estimate every task without running it.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import threading
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, CancelledError, Future, ThreadPoolExecutor, wait
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from atlas.api_http import Cancelled, TransientGaveUp
from atlas.jobs import (
    LOCK,
    PROGRESS,
    STOP,
    ProgressFile,
    RunLock,
    RunStopped,
    StopFlag,
    now_iso,
    process_started_epoch,
)
from atlas.llm import LlmConfigError, OpenAICompatLLM, extract_json
from atlas.state import work_release

JOBS: dict[str, str] = {"label": "atlas.label:label_job", "merge": "atlas.review:merge_job",
                        "narrative": "atlas.narrative:narrative_job", "brief": "atlas.narrative:brief_job",
                        "methods": "atlas.methods:methods_job"}
PROGRESS_EVERY_S = 5.0
# the command that continues a stopped job (`atlas run` or `atlas llm`, set by the CLI) — shown by `atlas status`
RESUME_COMMAND: ContextVar[str] = ContextVar("atlas_llm_resume", default="uv run atlas llm")

REPAIR = ("The reply above does not match the required JSON format ({error}). "
          "Reply again with ONLY the corrected JSON object, nothing else.")
REGENERATE = ("Your previous answer was rejected: {error}. Use only the facts, numbers and names given above; "
              "do not add any other number or topic name.")


@dataclass
class LlmItem:
    key: str                                              # e.g. "T000123" — names the item in logs and results
    prompt: str
    fallback: dict
    check: Callable[[dict], str | None] | None = None    # extra content check → error text or None


@dataclass
class LlmJob:
    task: str                                             # a key of llm.tasks
    schema: type[BaseModel]
    prompt_version: str
    items: list[LlmItem]


@dataclass
class LlmResult:
    output: dict
    source: str                                           # llm | cache | fallback
    repaired: int = 0
    key: str = ""                                         # cache key (empty for a fallback)


def llm_dir(cfg: dict) -> Path:
    return Path(cfg["pipeline"]["state_dir"]) / "llm_cache"


def _read_jsonl(path: Path) -> list[dict]:
    out = []
    if path.exists():
        # bytes + errors="replace": a hard kill can cut a Thai multibyte character; that must not fail the load
        for line in path.read_bytes().decode("utf-8", errors="replace").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue                                  # a line cut by a crash is skipped
            if isinstance(rec, dict):
                out.append(rec)
    return out


class LlmRunner:
    def __init__(self, cfg: dict, job: LlmJob, llm=None):
        lc = cfg["llm"]
        self.cfg, self.job, self.llm = cfg, job, llm
        self.tcfg = lc["tasks"][job.task]
        self.ecfg = lc["endpoints"][self.tcfg["endpoint"]]
        self.model_id = llm.model_id if llm is not None else self.tcfg["model"]
        self.budget = lc["budget_usd"]
        self.priced = self.ecfg["price_per_mtok_in"] is not None and self.ecfg["price_per_mtok_out"] is not None
        if self.budget is not None and not self.priced:
            raise LlmConfigError(f"llm.budget_usd needs price_per_mtok_in/out on llm.endpoints.{self.tcfg['endpoint']}")
        self.max_repairs, self.max_regen = int(lc["max_repairs"]), int(lc["max_regenerations"])
        self.dir = llm_dir(cfg)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.dir / f"{job.task}.jsonl"
        self.release = work_release(cfg)                  # spend is booked to the work_dir's release
        self._mutex = threading.Lock()
        records = _read_jsonl(self.cache_path)
        self.cache = {r["key"]: r for r in records if r.get("output") is not None}
        self.spent = sum(float(r.get("cost_usd", 0.0)) for p in self.dir.glob("*.jsonl")
                         for r in (records if p == self.cache_path else _read_jsonl(p))
                         if r.get("release") == self.release)
        self.stats = {"task": job.task, "model": self.model_id, "items": len(job.items), "from_cache": 0,
                      "generated": 0, "repaired": 0, "fallback": 0, "cost_usd": 0.0}
        self.stopping: str | None = None                  # "stop.flag" | "Ctrl-C" | "budget" | "error"
        self.retries, self.last_error, self.last_error_at = 0, None, None
        self.backoff_until = 0.0
        self.started_at = now_iso()

    # ------------------------------------------------------------------ cache and money
    def key_for(self, prompt: str) -> str:
        return hashlib.sha256(f"{self.model_id}\n{self.job.prompt_version}\n{prompt}".encode()).hexdigest()[:16]

    def _append(self, rec: dict) -> None:
        with self._mutex:
            lead = b""
            if self.cache_path.exists() and self.cache_path.stat().st_size:
                with open(self.cache_path, "rb") as r:
                    r.seek(-1, 2)
                    if r.read(1) != b"\n":
                        lead = b"\n"                        # a record cut by a crash: start a fresh line
            with open(self.cache_path, "ab") as f:
                f.write(lead + (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8"))
                f.flush()
            if rec.get("output") is not None:
                self.cache[rec["key"]] = rec

    def _price(self, tokens_in: float, tokens_out: float) -> float:
        if not self.priced:
            return 0.0
        return (tokens_in * float(self.ecfg["price_per_mtok_in"])
                + tokens_out * float(self.ecfg["price_per_mtok_out"])) / 1e6

    def estimate(self, prompt: str) -> float:
        """Upper bound for one call: ~1 token per character (Thai) + the full output allowance."""
        return self._price(len(prompt), int(self.tcfg["max_output_tokens"]))

    # ------------------------------------------------------------------ one item (worker thread)
    def _one(self, llm, k: str, item: LlmItem) -> LlmResult:
        messages = [{"role": "user", "content": item.prompt}]
        repairs = regens = 0
        cost = 0.0
        result = None
        try:
            while result is None:
                reply = llm.chat(messages)
                cost += (self._price(reply.prompt_tokens, reply.completion_tokens) if reply.prompt_tokens
                         else self._price(sum(len(m["content"]) for m in messages), len(reply.text)))
                try:
                    data = self.job.schema.model_validate(extract_json(reply.text)).model_dump()
                except ValueError as e:                         # bad JSON or pydantic ValidationError
                    if repairs >= self.max_repairs:
                        result = LlmResult(item.fallback, "fallback", repairs)
                        break
                    repairs += 1
                    messages = messages + [{"role": "assistant", "content": reply.text},
                                           {"role": "user", "content": REPAIR.format(error=str(e)[:300])}]
                    continue
                error = item.check(data) if item.check else None
                if error:
                    if regens >= self.max_regen:
                        print(f"[llm:{self.job.task}] {item.key}: {error} — fallback")
                        result = LlmResult(item.fallback, "fallback", repairs)
                        break
                    regens += 1
                    messages = [{"role": "user", "content": item.prompt + "\n\n" + REGENERATE.format(error=error)}]
                    continue
                result = LlmResult(data, "llm", repairs, k)
        except Exception as e:
            # paid turns of an item that then failed (give-up, config error, cancel): journal the cost so it
            # counts against the release budget after a restart; output=None keeps it out of the cache
            if cost > 0:
                self._append({"key": k, "item": item.key, "task": self.job.task, "model": self.model_id,
                              "prompt_version": self.job.prompt_version, "release": self.release,
                              "output": None, "cost_usd": round(cost, 6), "repaired": repairs,
                              "error": type(e).__name__, "at": now_iso()})
            raise
        finally:
            with self._mutex:
                self.spent += cost
                self.stats["cost_usd"] += cost
        self._append({"key": k, "item": item.key, "task": self.job.task, "model": self.model_id,
                      "prompt_version": self.job.prompt_version, "release": self.release,
                      "output": result.output if result.source == "llm" else None,
                      "cost_usd": round(cost, 6), "repaired": repairs, "at": now_iso()})
        return result

    def on_event(self, kind: str, info: dict) -> None:   # from worker threads (OpenAICompatLLM retries)
        if kind == "retry":
            with self._mutex:
                self.retries += 1
                self.backoff_until = max(self.backoff_until, time.monotonic() + float(info.get("delay") or 0))
                self.last_error, self.last_error_at = info.get("error"), now_iso()

    # ------------------------------------------------------------------ heartbeat for `atlas status`
    def _snapshot(self, status: str) -> dict:
        s = self.stats
        done = s["from_cache"] + s["generated"] + s["fallback"]
        if status == "running" and time.monotonic() < self.backoff_until:
            status = "backing_off"
        return {"kind": "llm", "unit": "items", "job_id": f"llm:{self.job.task}", "task": self.job.task,
                "model": self.model_id, "status": status, "pid": os.getpid(), "total": s["items"],
                "cached": s["from_cache"], "this_run": s["generated"] + s["fallback"], "remaining": s["items"] - done,
                "generated": s["generated"], "repaired": s["repaired"], "fallback": s["fallback"],
                "retries": self.retries, "truncated": 0, "cost_usd": round(s["cost_usd"], 4),
                "release": self.release, "release_spend_usd": round(self.spent, 4), "budget_usd": self.budget,
                "stop_reason": self.stopping if status == "stopped" else None, "resume": RESUME_COMMAND.get(),
                "last_error": self.last_error, "last_error_at": self.last_error_at,
                "started_at": self.started_at, "updated_at": now_iso()}

    # ------------------------------------------------------------------ the job
    def run(self) -> tuple[dict[str, LlmResult], dict]:
        results: dict[str, LlmResult] = {}
        todo: list[tuple[str, LlmItem]] = []
        for it in self.job.items:
            k = self.key_for(it.prompt)
            if k in self.cache:
                results[it.key] = LlmResult(self.cache[k]["output"], "cache", 0, k)
            else:
                todo.append((k, it))
        self.stats["from_cache"] = len(results)
        if todo:
            lock = RunLock(self.dir / LOCK, stale_seconds=float(self.cfg["llm"]["lock_stale_seconds"]),
                           heartbeat=self.dir / PROGRESS)
            lock.acquire()                                    # jobs.LockHeld when another LLM job runs
            try:
                self._run_todo(todo, results)
            finally:
                lock.release()
        self.stats["cost_usd"] = round(self.stats["cost_usd"], 6)
        return results, self.stats

    def _run_todo(self, todo: list[tuple[str, LlmItem]], results: dict[str, LlmResult]) -> None:
        llm = self.llm or OpenAICompatLLM.for_task(self.cfg, self.job.task)
        hooked = hasattr(llm, "on_event")
        previous = llm.on_event if hooked else None
        if hooked:
            llm.on_event = self.on_event
        stop_flag = StopFlag(self.dir / STOP)
        stop_flag.clear_if_older(process_started_epoch())   # a flag left by an earlier run; a newer one is honoured
        pf = ProgressFile(self.dir / PROGRESS, min_interval=PROGRESS_EVERY_S)
        pf.write(self._snapshot("running"), force=True)
        n = max(1, int(self.ecfg["concurrency"]))
        pending = iter(todo)
        nxt = next(pending, None)
        in_flight: dict[Future, tuple[str, LlmItem, float]] = {}
        reserved = 0.0                                        # budget held by calls in flight (upper bounds)
        failure: Exception | None = None
        ex = ThreadPoolExecutor(max_workers=n, thread_name_prefix="llm")

        def begin_stop(why: str) -> None:
            if self.stopping is None:
                self.stopping = why
                for f in in_flight:
                    f.cancel()                                # queued calls never start (not paid)
                cancel = getattr(llm, "cancel", None)
                if cancel:
                    cancel()                                  # a worker in a backoff wait gives up
                if why not in ("error", "budget"):
                    print(f"[llm:{self.job.task}] stopping ({why}): waiting for the calls in flight")

        try:
            while True:
                if self.stopping is None and stop_flag.is_set():
                    begin_stop("stop.flag")
                while self.stopping is None and nxt is not None and len(in_flight) < n:
                    k, it = nxt
                    # worst case for one item: the first call + every repair + every regeneration, each at the
                    # full estimate (real cost is almost always far below it)
                    est = self.estimate(it.prompt) * (1 + self.max_repairs + self.max_regen)
                    if self.budget is not None and self.spent + reserved + est > float(self.budget):
                        if not in_flight:                     # nothing will free budget: stop here
                            begin_stop("budget")
                        break                                 # else wait: real costs are below the estimates
                    in_flight[ex.submit(self._one, llm, k, it)] = (k, it, est)
                    reserved += est
                    nxt = next(pending, None)
                if not in_flight:
                    break
                try:
                    done, _ = wait(list(in_flight), timeout=0.5, return_when=FIRST_COMPLETED)
                except KeyboardInterrupt:
                    begin_stop("Ctrl-C")
                    continue
                for fut in done:
                    k, it, est = in_flight.pop(fut)
                    reserved -= est
                    try:
                        res = fut.result()
                    except LlmConfigError as e:
                        failure = failure or e
                        begin_stop("error")
                        continue
                    except TransientGaveUp as e:              # only when max_retries is set
                        print(f"[llm:{self.job.task}] {it.key}: {e} — fallback (asked again next run)")
                        res = LlmResult(it.fallback, "fallback")
                    except (Cancelled, CancelledError):       # stopped mid-backoff / never started: asked next run
                        continue
                    except Exception as e:  # noqa: BLE001 — a bug: keep what was paid for, then re-raise it
                        failure = failure or e
                        begin_stop("error")
                        continue
                    results[it.key] = res
                    self.stats["generated" if res.source == "llm" else "fallback"] += 1
                    self.stats["repaired"] += int(res.source == "llm" and res.repaired > 0)
                pf.write(self._snapshot("running"))
        finally:
            ex.shutdown(wait=True, cancel_futures=True)
            if hooked:
                llm.on_event = previous
        if failure is not None:
            self.last_error, self.last_error_at = f"{type(failure).__name__}: {failure}", now_iso()
            pf.write(self._snapshot("failed"), force=True)
            raise failure
        if self.stopping is not None:
            pf.write(self._snapshot("stopped"), force=True)
            stop_flag.clear()
            left = len(todo) - self.stats["generated"] - self.stats["fallback"]
            why = (f"budget llm.budget_usd = {self.budget} USD reached ({round(self.spent, 4)} USD spent in "
                   f"{self.release}) — raise it" if self.stopping == "budget" else f"{self.stopping}")
            raise RunStopped(f"LLM task {self.job.task}: {why}; {left} of {len(todo)} items not done — run the same "
                             f"command again to continue (finished calls are cached, nothing is paid twice)")
        # no stop_flag.clear() here: a stop requested as the job ends must still stop the next task; a flag older
        # than this process is discarded by clear_if_older at the next job start
        pf.write(self._snapshot("done"), force=True)

    def dry_run(self) -> dict:
        todo = [it for it in self.job.items if self.key_for(it.prompt) not in self.cache]
        chars = sum(len(it.prompt) for it in todo)
        out_tokens = len(todo) * int(self.tcfg["max_output_tokens"])
        return {"task": self.job.task, "model": self.model_id, "items": len(self.job.items),
                "cached": len(self.job.items) - len(todo), "to_call": len(todo), "est_input_tokens": chars,
                "max_output_tokens": out_tokens,
                "est_cost_usd": round(self._price(chars, out_tokens), 4) if self.priced else None,
                "release_spend_usd": round(self.spent, 4), "budget_usd": self.budget}


def run_job(cfg: dict, job: LlmJob, llm=None) -> tuple[dict[str, LlmResult], dict]:
    """Results for every item (cache, LLM or fallback) + stats for the step's meta file.
    Raises LlmConfigError (endpoint/config), jobs.LockHeld (another LLM job) or jobs.RunStopped (stop/budget)."""
    return LlmRunner(cfg, job, llm).run()


# ---------------------------------------------------------------------- CLI helpers
def build_job(cfg: dict, task: str) -> LlmJob:
    module, fn = JOBS[task].split(":")
    return getattr(importlib.import_module(module), fn)(cfg)


def dry_run_all(cfg: dict, tasks: list[str] | None = None) -> list[dict]:
    rows = []
    # methods notes are opt-in: without methods.provider: llm the task is not part of the default estimate
    default = [t for t in JOBS if t != "methods" or cfg["methods"]["provider"] == "llm"]
    for task in tasks or default:
        try:
            rows.append(LlmRunner(cfg, build_job(cfg, task)).dry_run())
        except FileNotFoundError as e:
            rows.append({"task": task, "skipped": f"missing checkpoint {Path(str(e.filename or e)).name} — "
                                                  "run the pipeline up to that step first"})
    return rows


def release_spend(cfg: dict, task: str, release: str) -> float:
    """USD a task spent on `release` over every run (its journal, incl. paid calls that ended in a fallback)."""
    return sum(float(r.get("cost_usd", 0.0)) for r in _read_jsonl(llm_dir(cfg) / f"{task}.jsonl")
               if r.get("release") == release and r.get("task", task) == task)


def request_stop(cfg: dict) -> Path:
    flag = StopFlag(llm_dir(cfg) / STOP)
    flag.request()
    return flag.path


def status_extra(info: dict) -> list[str]:
    """LLM lines added under the generic jobs.format_job_status block of `atlas status`."""
    spend = f"{info.get('release_spend_usd', 0)} USD in {info.get('release', '?')}"
    if info.get("budget_usd") is not None:
        spend += f" (budget {info['budget_usd']})"
    lines = [f"  task / model          : {info.get('task')} · {info.get('model')}",
             f"  llm                   : new {int(info.get('generated') or 0):,} · repaired "
             f"{int(info.get('repaired') or 0):,} · fallback {int(info.get('fallback') or 0):,}",
             f"  cost                  : {info.get('cost_usd', 0)} USD this run · {spend}"]
    if info.get("stop_reason"):
        lines.append(f"  stopped by            : {info['stop_reason']} — run `{info.get('resume') or 'uv run atlas llm'}` "
                     f"again to continue")
    return lines


def check_endpoints(cfg: dict, transport=None, sleep=None) -> list[dict]:
    """One tiny JSON request per distinct (endpoint, model) used by llm.tasks: reachable? JSON? Thai intact?"""
    word, out, seen = "ภาษาไทย", [], set()
    prompt = f'Reply with ONLY this JSON object, unchanged: {{"ok": true, "word": "{word}"}}'
    for task, tcfg in cfg["llm"]["tasks"].items():
        pair = (tcfg["endpoint"], tcfg["model"])
        if not tcfg["model"] or pair in seen:
            continue
        seen.add(pair)
        row = {"endpoint": pair[0], "model": pair[1], "tasks": task, "seconds": None, "json_ok": False,
               "thai_ok": False, "error": ""}
        try:
            llm = OpenAICompatLLM.for_task(cfg, task, transport=transport, sleep=sleep, max_retries=2)
            reply = llm.chat([{"role": "user", "content": prompt}])
            data = extract_json(reply.text)
            row.update(seconds=round(reply.seconds, 2), json_ok=True, thai_ok=data.get("word") == word)
        except Exception as e:  # noqa: BLE001 — reported to the operator, not raised
            row["error"] = f"{type(e).__name__}: {e}"
        out.append(row)
    for row in out:
        row["tasks"] = ", ".join(t for t, c in cfg["llm"]["tasks"].items()
                                 if (c["endpoint"], c["model"]) == (row["endpoint"], row["model"]))
    return out
