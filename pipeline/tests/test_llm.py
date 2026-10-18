import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError, field_validator

from atlas.config import load_config
from atlas.jobs import LOCK, LockHeld, RunLock, RunStopped
from atlas.llm import LlmConfigError, OpenAICompatLLM, extract_json
from atlas.llm_runner import LlmItem, LlmJob, LlmRunner, check_endpoints, llm_dir, request_stop, run_job
from atlas.prompts import load_prompt, placeholders, prompt_version, render_prompt

REPO = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- prompts
def test_every_master_prompt_loads_and_label_placeholders_are_known():
    for p in sorted((REPO / "prompts").glob("*.md")):
        assert load_prompt(p.stem, REPO / "prompts")
    assert placeholders(load_prompt("topic_label.th", REPO / "prompts")) == {"keywords", "terms", "titles"}


def test_render_inserts_values_verbatim_and_requires_every_placeholder():
    t = load_prompt("topic_label.th")
    out = render_prompt(t, keywords="ข้าว; rice", terms="ชาวนา {x}", titles="- การปลูกข้าว")
    assert "ชาวนา {x}" in out and "{keywords}" not in out
    with pytest.raises(KeyError, match="titles"):
        render_prompt(t, keywords="a", terms="b")


def test_crlf_prompt_file_loads_identically_and_version_hashes_the_template_only(tmp_path):
    text = (REPO / "prompts" / "topic_label.th.md").read_text(encoding="utf-8")
    (tmp_path / "topic_label.th.md").write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    t = load_prompt("topic_label.th", tmp_path)
    assert t == load_prompt("topic_label.th", REPO / "prompts")
    (tmp_path / "topic_label.th.md").write_text("# new notes\n\n" + text, encoding="utf-8")
    assert prompt_version(load_prompt("topic_label.th", tmp_path)) == prompt_version(t)
    assert len(prompt_version(t)) == 12 and prompt_version(t + " ") != prompt_version(t)


def test_extract_json_tolerates_fences_and_rejects_garbage():
    assert extract_json('Sure:\n```json\n{"a": 1}\n```') == {"a": 1}
    for bad in ("no json here", "[1, 2]"):
        with pytest.raises(ValueError):
            extract_json(bad)


# ---------------------------------------------------------------- adapter (fake api_http transport, no network)
def ok(text: str, usage=(100, 20)):
    body = {"choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": usage[0], "completion_tokens": usage[1]}}
    return 200, {}, json.dumps(body, ensure_ascii=False).encode("utf-8")


class FakeServer:
    """api_http Transport: (url, headers, body, timeout) → (status, headers, body); scripted replies."""

    def __init__(self, *replies, default=None):
        self.replies, self.default, self.requests = list(replies), default, []

    def __call__(self, url, headers, body, timeout):
        self.requests.append({"url": url, "headers": headers, "payload": json.loads(body)})
        r = self.replies.pop(0) if self.replies else self.default
        if isinstance(r, Exception):
            raise r
        return r(self.requests[-1]["payload"]) if callable(r) else r


def _cfg(make_cfg, tmp_path, **endpoint):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q4"
    cfg["llm"]["endpoints"]["default"].update(base_url="https://llm.example/v1", concurrency=1, **endpoint)
    for t in cfg["llm"]["tasks"].values():
        t["model"] = "test-model"
    return cfg


def _llm(cfg, server, task="label", sleeps=None):
    return OpenAICompatLLM.for_task(cfg, task, transport=server,
                                    sleep=(sleeps.append if sleeps is not None else lambda s: None))


def test_adapter_sends_an_openai_compatible_request(make_cfg, tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_LLM_API_KEY", "sk-test")
    cfg = _cfg(make_cfg, tmp_path)
    server = FakeServer(ok('{"name": "ข้าว"}'), ok('{"name": "ข้าว"}'))
    reply = _llm(cfg, server).chat([{"role": "user", "content": "ตั้งชื่อ"}])
    req = server.requests[0]
    assert req["url"] == "https://llm.example/v1/chat/completions"
    assert req["headers"]["Authorization"] == "Bearer sk-test"
    p = req["payload"]
    assert (p["model"], p["messages"][0]["content"], p["max_tokens"]) == ("test-model", "ตั้งชื่อ", 600)
    assert p["response_format"] == {"type": "json_object"} and reply.prompt_tokens == 100
    cfg["llm"]["endpoints"]["default"]["json_mode"] = False
    _llm(cfg, server).chat([{"role": "user", "content": "x"}])
    assert "response_format" not in server.requests[1]["payload"]


def test_transient_errors_retry_with_retry_after(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    sleeps = []
    server = FakeServer((503, {}, b"busy"), (429, {"Retry-After": "7"}, b"slow down"), ConnectionResetError("reset"),
                        (200, {}, b'{"error": {"message": "upstream timeout"}}'), ok('{"name": "ok"}'))
    assert _llm(cfg, server, sleeps=sleeps).chat([{"role": "user", "content": "x"}]).text == '{"name": "ok"}'
    assert len(server.requests) == 5 and 7.0 in sleeps


def test_permanent_error_raises_at_once_and_names_the_key_variable(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    server = FakeServer((401, {}, b'{"error": "invalid api key"}'))
    with pytest.raises(LlmConfigError, match="ATLAS_LLM_API_KEY"):
        _llm(cfg, server).chat([{"role": "user", "content": "x"}])
    assert len(server.requests) == 1


# ---------------------------------------------------------------- runner
class Out(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("blank name")
        return v.strip()


def _job(keys, check=None):
    return LlmJob("label", Out, "v1", [LlmItem(k, f"name item {k}", {"name": f"fallback {k}"}, check) for k in keys])


def _by_item(script: dict):
    """Reply chosen by the item named in the first message; the turn number is len(messages)."""
    def reply(payload):
        item = payload["messages"][0]["content"].split("item ")[1].split()[0]
        texts = script[item]
        turn = len(payload["messages"]) // 2
        return ok(texts[min(turn, len(texts) - 1)])
    return reply


def test_runner_caches_repairs_and_falls_back(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    script = {"a": ['{"name": "A"}'], "b": ["not json", '{"name": "B"}'], "c": ['{"name": " "}']}
    server = FakeServer(default=_by_item(script))
    res, stats = run_job(cfg, _job(["a", "b", "c"]), llm=_llm(cfg, server))
    assert {k: (r.output["name"], r.source) for k, r in res.items()} == {
        "a": ("A", "llm"), "b": ("B", "llm"), "c": ("fallback c", "fallback")}
    assert (stats["generated"], stats["repaired"], stats["fallback"]) == (2, 1, 1)
    assert len(server.requests) == 1 + 2 + 3                 # c: first try + max_repairs (2)
    repair_turn = server.requests[2]["payload"]["messages"]
    assert [m["role"] for m in repair_turn] == ["user", "assistant", "user"] and "JSON" in repair_turn[2]["content"]
    again = FakeServer(default=_by_item({**script, "c": ['{"name": "C"}']}))
    res, stats = run_job(cfg, _job(["a", "b", "c"]), llm=_llm(cfg, again))
    assert len(again.requests) == 1 and stats["from_cache"] == 2 and res["c"].output == {"name": "C"}
    lines = (llm_dir(cfg) / "label.jsonl").read_text(encoding="utf-8").splitlines()
    assert sum(json.loads(x)["output"] is not None for x in lines) == 3


def test_failed_content_check_regenerates_once_then_falls_back(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    seen = {"good": 0}

    def reply(payload):
        item = payload["messages"][0]["content"].split("item ")[1].split()[0]
        if item == "good":
            seen["good"] += 1
            return ok('{"name": "invented 99"}' if seen["good"] == 1 else '{"name": "grounded"}')
        return ok('{"name": "invented 99"}')

    def check(out):
        return "number 99 is not in the facts" if "99" in out["name"] else None

    server = FakeServer(default=reply)
    res, stats = run_job(cfg, _job(["good", "bad"], check), llm=_llm(cfg, server))
    assert res["good"].output == {"name": "grounded"} and res["bad"].source == "fallback"
    regen = [r for r in server.requests if "rejected" in r["payload"]["messages"][0]["content"]]
    assert len(regen) == 2 and len(server.requests) == 4


def test_transient_give_up_falls_back_and_is_not_cached(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path, max_retries=1)
    res, stats = run_job(cfg, _job(["a"]), llm=_llm(cfg, FakeServer(default=(502, {}, b"bad gateway"))))
    assert res["a"].source == "fallback" and stats["fallback"] == 1
    res, _ = run_job(cfg, _job(["a"]), llm=_llm(cfg, FakeServer(default=ok('{"name": "A"}'))))
    assert res["a"].output == {"name": "A"}                   # asked again, not served from the cache


def test_budget_stops_cleanly_and_a_rerun_continues(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path, price_per_mtok_in=1.0, price_per_mtok_out=1.0)
    cfg["llm"]["budget_usd"] = 0.0012                         # one call costs 120 tokens ≈ 0.00012 USD
    keys = [f"k{i}" for i in range(12)]
    server = FakeServer(default=lambda p: ok('{"name": "n"}'))
    with pytest.raises(RunStopped, match="budget"):
        run_job(cfg, _job(keys), llm=_llm(cfg, server))
    done = len(server.requests)
    prog = json.loads((llm_dir(cfg) / "progress.json").read_text(encoding="utf-8"))
    assert 0 < done < 12 and (prog["status"], prog["stop_reason"], prog["kind"]) == ("stopped", "budget", "llm")
    cfg["llm"]["budget_usd"] = None
    more = FakeServer(default=lambda p: ok('{"name": "n"}'))
    res, stats = run_job(cfg, _job(keys), llm=_llm(cfg, more))
    assert stats["from_cache"] == done and len(more.requests) == 12 - done and len(res) == 12


def test_stop_flag_ends_the_job_after_the_calls_in_flight(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)

    def reply(payload):
        request_stop(cfg)                                     # operator runs `atlas llm-stop` meanwhile
        return ok('{"name": "n"}')

    server = FakeServer(default=reply)
    with pytest.raises(RunStopped, match="stop.flag"):
        run_job(cfg, _job(["a", "b", "c"]), llm=_llm(cfg, server))
    assert len(server.requests) == 1 and not (llm_dir(cfg) / "stop.flag").exists()
    res, stats = run_job(cfg, _job(["a", "b", "c"]), llm=_llm(cfg, FakeServer(default=ok('{"name": "n"}'))))
    assert stats["from_cache"] == 1 and stats["generated"] == 2


def test_permanent_error_stops_the_job_and_keeps_finished_items(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    server = FakeServer(ok('{"name": "A"}'), (404, {}, b"model not found"))
    with pytest.raises(LlmConfigError, match="404"):
        run_job(cfg, _job(["a", "b", "c"]), llm=_llm(cfg, server))
    prog = json.loads((llm_dir(cfg) / "progress.json").read_text(encoding="utf-8"))
    assert prog["status"] == "failed" and "404" in prog["last_error"] and len(server.requests) == 2
    res, stats = run_job(cfg, _job(["a"]), llm=_llm(cfg, FakeServer()))
    assert res["a"].source == "cache"


def test_second_job_is_refused_while_the_lock_is_held(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    with RunLock(llm_dir(cfg) / LOCK):                        # another LLM job holds the OS lock
        with pytest.raises(LockHeld):
            run_job(cfg, _job(["a"]), llm=_llm(cfg, FakeServer(default=ok('{"name": "n"}'))))


def test_cached_items_need_no_endpoint_and_status_and_dry_run_report(make_cfg, tmp_path):
    from atlas.cli import render_status

    cfg = _cfg(make_cfg, tmp_path, price_per_mtok_in=0.5, price_per_mtok_out=2.0)
    run_job(cfg, _job(["a", "b"]), llm=_llm(cfg, FakeServer(default=ok('{"name": "n"}'))))
    cfg["llm"]["endpoints"]["default"]["base_url"] = ""               # nothing left to pay for → no client needed
    res, stats = run_job(cfg, _job(["a", "b"]))
    assert stats["from_cache"] == 2 and {r.source for r in res.values()} == {"cache"}
    text = render_status(cfg)                                          # the P0 `atlas status` lists the LLM job
    assert "llm:label" in text and "done" in text and "2 / 2 items" in text and "test-model" in text
    dry = LlmRunner(cfg, _job(["a", "b", "c"])).dry_run()
    assert (dry["cached"], dry["to_call"]) == (2, 1) and dry["est_cost_usd"] > 0


def test_check_endpoints_reports_json_and_thai_round_trip(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    cfg["llm"]["tasks"]["brief"]["model"] = "other-model"
    server = FakeServer(ok('{"ok": true, "word": "ภาษาไทย"}'), (401, {}, b"bad key"))
    rows = check_endpoints(cfg, transport=server, sleep=lambda s: None)
    assert [(r["model"], r["json_ok"], r["thai_ok"]) for r in rows] == [("test-model", True, True),
                                                                        ("other-model", False, False)]
    assert rows[0]["tasks"] == "label, merge, narrative" and "LlmConfigError" in rows[1]["error"]


def test_llm_config_defaults_and_errors(make_cfg, tmp_path):
    cfg = load_config(None)
    assert cfg["llm"]["endpoints"]["default"]["api_key_env"] == "ATLAS_LLM_API_KEY"
    assert set(cfg["llm"]["tasks"]) == {"label", "merge", "narrative", "brief"}
    with pytest.raises(LlmConfigError, match="llm.tasks.label.model"):
        OpenAICompatLLM.for_task(make_cfg(tmp_path), "label")
    priced = _cfg(make_cfg, tmp_path)
    priced["llm"]["budget_usd"] = 5.0
    with pytest.raises(LlmConfigError, match="price_per_mtok"):
        LlmRunner(priced, _job(["a"]))
    p = tmp_path / "c.yaml"
    p.write_text("llm:\n  tasks:\n    label:\n      endpoint: nowhere\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="nowhere"):
        load_config(p)


def test_cli_check_without_models_exits_2():
    from typer.testing import CliRunner

    from atlas.cli import app

    r = CliRunner().invoke(app, ["llm", "--check"])
    assert r.exit_code == 2 and "nothing to check" in r.output


def test_cli_llm_stop_writes_the_flag(tmp_path):
    from typer.testing import CliRunner

    from atlas.cli import app

    p = tmp_path / "c.yaml"
    p.write_text(f"pipeline:\n  state_dir: {(tmp_path / 'state').as_posix()}\n", encoding="utf-8")
    r = CliRunner().invoke(app, ["llm-stop", "-c", str(p)])
    assert r.exit_code == 0 and (tmp_path / "state" / "llm_cache" / "stop.flag").exists()


def test_cli_llm_background_reports_a_child_that_fails_at_once(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from atlas.cli import app

    monkeypatch.setenv("ATLAS_BACKGROUND_CHECK_S", "60")
    p = tmp_path / "c.yaml"
    p.write_text(f"pipeline:\n  state_dir: {(tmp_path / 'state').as_posix()}\n"
                 f"  work_dir: {(tmp_path / 'work').as_posix()}\n", encoding="utf-8")
    r = CliRunner().invoke(app, ["llm", "-c", str(p), "--background"])
    assert r.exit_code == 1 and "04_topic_info" in r.output           # the tail of run.log is shown
