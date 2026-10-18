"""LLM access — one OpenAI-compatible adapter: POST {base_url}/chat/completions.

Works with OpenRouter, Typhoon, DeepInfra, Together, an organisation's vLLM / LiteLLM gateway, and
OpenAI / Gemini / Claude models behind such a gateway. HTTP, error classification, backoff and the retry
loop are the P0 core in atlas.api_http (shared with atlas.embed_api), so the LLM behaves like the embedding
runner: transient failures (408/409/425/429/5xx, network, a 2xx without `choices`) retry with capped
full-jitter backoff and Retry-After — without limit unless max_retries is set, then api_http.TransientGaveUp —
while permanent ones (3xx, 401/402/403/404, other 4xx, 429 out of quota) and "prompt too large" raise
LlmConfigError at once with the fix in the message. `response_format: {"type": "json_object"}` is sent only
when the endpoint says json_mode: true; replies are always parsed by extract_json and validated by the
caller's pydantic schema (atlas.llm_runner).

config:  llm.endpoints.<name> = {base_url, api_key_env, json_mode, concurrency, request_timeout,
                                 max_retries, backoff_initial, backoff_max, price_per_mtok_in/out}
         llm.tasks.<task>     = {endpoint, model, temperature, max_output_tokens}
"""
from __future__ import annotations

import json
import os
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from atlas.api_http import (
    ApiConfigError,
    EventHandler,
    HttpPermanentError,
    MalformedResponse,
    RetryPolicy,
    TooLargeError,
    Transport,
    call_with_retry,
    explain_permanent,
    post_json,
    urllib_transport,
    validate_base_url,
)

MALFORMED_REPEAT = 3        # the same malformed 2xx answer this often in a row = not transient (cf. embed_api)


class LlmConfigError(ApiConfigError):
    """Wrong endpoint / key / model / quota, or a prompt the model cannot take — retrying will not help."""


class _PersistentMalformed(Exception):
    """The server gave the same malformed 2xx answer MALFORMED_REPEAT times in a row."""


def extract_json(text: str) -> dict:
    """Parse the JSON object in a reply that may carry prose or ```json fences around it."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in reply")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("reply JSON is not an object")
    return data


@dataclass
class Reply:
    text: str
    prompt_tokens: int          # 0 when the server reports no usage
    completion_tokens: int
    seconds: float


class OpenAICompatLLM:
    """`.chat(messages) -> Reply`. `on_event(kind, info)` (kind "retry") may be set later — the runner
    subscribes to it; `cancel()` makes a worker in a backoff wait raise api_http.Cancelled."""

    def __init__(self, base_url: str, model: str, temperature: float, max_output_tokens: int, *,
                 api_key: str = "", api_key_env: str = "", json_mode: bool = False, timeout: float = 120.0,
                 policy: RetryPolicy | None = None, transport: Transport | None = None,
                 on_event: EventHandler | None = None):
        self.base_url = str(base_url).rstrip("/")
        self.url = self.base_url + "/chat/completions"
        try:
            validate_base_url(self.url)
        except ApiConfigError as e:
            raise LlmConfigError(str(e)) from None
        self.model, self.temperature, self.max_output_tokens = model, temperature, max_output_tokens
        self.model_id = model                    # part of every LLM cache key
        self.json_mode, self.timeout, self.api_key_env = json_mode, timeout, api_key_env
        self.__headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.policy = policy or RetryPolicy(2.0, 300.0, None)
        self.transport = transport or urllib_transport
        self.on_event = on_event

    @classmethod
    def for_task(cls, cfg: dict, task: str, transport: Transport | None = None,
                 sleep: Callable[[float], Any] | None = None, max_retries: int | None = -1) -> OpenAICompatLLM:
        """The client of llm.tasks.<task>. max_retries=-1 → the endpoint's setting (a check passes a small one)."""
        tcfg = cfg["llm"]["tasks"][task]
        ecfg = cfg["llm"]["endpoints"][tcfg["endpoint"]]
        if not ecfg["base_url"] or not tcfg["model"]:
            raise LlmConfigError(f"set llm.endpoints.{tcfg['endpoint']}.base_url and llm.tasks.{task}.model "
                                 f"(or switch the step that needs the LLM off)")
        retries = ecfg["max_retries"] if max_retries == -1 else max_retries
        policy = RetryPolicy(float(ecfg["backoff_initial"]), float(ecfg["backoff_max"]), retries, sleep=sleep,
                             rand=random.random)
        return cls(ecfg["base_url"], tcfg["model"], float(tcfg["temperature"]), int(tcfg["max_output_tokens"]),
                   api_key=os.environ.get(ecfg["api_key_env"], "").strip(), api_key_env=ecfg["api_key_env"],
                   json_mode=bool(ecfg["json_mode"]), timeout=float(ecfg["request_timeout"]), policy=policy,
                   transport=transport)

    def cancel(self) -> None:
        self.policy.cancel()

    def _emit(self, kind: str, info: dict) -> None:
        if self.on_event:
            self.on_event(kind, info)

    def chat(self, messages: list[dict]) -> Reply:
        payload: dict = {"model": self.model, "messages": messages, "temperature": self.temperature,
                         "max_tokens": self.max_output_tokens}
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        seen = {"kind": None, "n": 0}

        def attempt() -> dict:
            try:
                data = post_json(self.transport, self.url, payload, headers=self.__headers, timeout=self.timeout)
                if not (isinstance(data, dict) and data.get("choices")):    # gateways wrap upstream errors in a 200
                    raise MalformedResponse(f"response without choices: {json.dumps(data)[:200]}", kind="no-choices")
                return data
            except MalformedResponse as e:
                seen["n"] = seen["n"] + 1 if e.kind == seen["kind"] else 1
                seen["kind"] = e.kind
                if seen["n"] >= MALFORMED_REPEAT:
                    raise _PersistentMalformed(str(e)) from None
                raise

        t0 = time.monotonic()
        try:
            data = call_with_retry(attempt, self.policy, self._emit)
        except HttpPermanentError as e:
            raise LlmConfigError(explain_permanent(e.status, e.body, key_env=self.api_key_env or "the API key env var",
                                                   base_url=self.base_url, model=self.model,
                                                   location=e.location)) from None
        except TooLargeError as e:
            raise LlmConfigError(f"{self.url} → {e} — the prompt is too long for {self.model}; use a model with a "
                                 "larger context or fewer representative titles") from None
        except _PersistentMalformed as e:
            raise LlmConfigError(f"{self.url} answered {MALFORMED_REPEAT} times without a usable reply ({e}) — "
                                 f"check base_url ({self.base_url}) and model ({self.model})") from None
        except LlmConfigError:
            raise
        except ApiConfigError as e:                               # TLS / bad URL found while sending
            raise LlmConfigError(str(e)) from None
        message = (data["choices"][0] or {}).get("message") or {}
        text = message.get("content") or ""                       # empty → the caller's JSON check asks for a repair
        usage = data.get("usage") or {}
        return Reply(text, int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0),
                     time.monotonic() - t0)
