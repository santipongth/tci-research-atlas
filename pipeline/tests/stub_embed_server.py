"""OpenAI-compatible stub embedding server for tests and manual end-to-end runs (no real model).

    POST {url}/embeddings  {"model", "input": [...]}  ->  {"data": [{"index", "embedding"}], "model"}

Vectors are a deterministic function of the text (see stub_vector). Failure injection: random 503s
(`fail_rate`), random 413s for multi-text batches (`too_large_rate`), 413 above `max_inputs` texts,
401 unless `Authorization: Bearer <require_key>` (when set), and a per-request `latency`. Counts what it served so tests can assert "only the remaining texts were sent".

In a test:     with StubEmbedServer(latency=0.05) as srv: cfg["embedding"]["api"]["base_url"] = srv.url
Standalone:    python tests/stub_embed_server.py --port 8765 --latency 0.2 --fail-rate 0.3
"""
from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import random
import threading
import time


def stub_vector(text: str, dim: int) -> list[float]:
    out: list[float] = []
    seed = text.encode("utf-8")
    while len(out) < dim:
        seed = hashlib.sha256(seed).digest()
        out += [b / 255.0 + 0.01 for b in seed]
    return out[:dim]


class StubEmbedServer:
    def __init__(self, *, dim: int = 8, latency: float = 0.0, fail_rate: float = 0.0, too_large_rate: float = 0.0,
                 max_inputs: int | None = None, require_key: str | None = None, seed: int = 0,
                 host: str = "127.0.0.1", port: int = 0):
        self.dim, self.latency, self.fail_rate, self.too_large_rate = dim, latency, fail_rate, too_large_rate
        self.max_inputs, self.require_key = max_inputs, require_key
        self._rng = random.Random(seed)
        self._lock = threading.Lock()
        self.texts_served: list[str] = []      # texts in successful (200) responses, in serve order
        self.n_requests = self.n_503 = self.n_413 = 0
        self.active = 0                          # requests being handled right now
        self._srv = http.server.ThreadingHTTPServer((host, port), self._handler())
        self._srv.daemon_threads = True
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        host, port = self._srv.server_address[:2]
        return f"http://{host}:{port}/v1"

    def reset_counts(self) -> None:
        with self._lock:
            self.texts_served.clear()
            self.n_requests = self.n_503 = self.n_413 = 0

    def wait_idle(self, timeout: float = 10.0) -> bool:
        """Wait until no request is being handled (e.g. a killed client's requests finished server-side)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if self.active == 0:
                    return True
            time.sleep(0.02)
        return False

    def start(self) -> StubEmbedServer:
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._srv.shutdown()
        self._srv.server_close()

    def __enter__(self) -> StubEmbedServer:
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    def _decide(self, n_texts: int) -> int:
        with self._lock:
            self.n_requests += 1
            if self.fail_rate and self._rng.random() < self.fail_rate:
                self.n_503 += 1
                return 503
            if n_texts > 1 and ((self.max_inputs and n_texts > self.max_inputs)
                                or (self.too_large_rate and self._rng.random() < self.too_large_rate)):
                self.n_413 += 1
                return 413
            return 200

    def _handler(self):
        stub = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _reply(self, status: int, payload: bytes, ctype: str = "application/json") -> None:
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_POST(self):  # noqa: N802
                with stub._lock:
                    stub.active += 1
                try:
                    self._post()
                finally:
                    with stub._lock:
                        stub.active -= 1

            def _post(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if not self.path.rstrip("/").endswith("/embeddings"):
                    return self._reply(404, b'{"error": "not found"}')
                if stub.require_key and self.headers.get("Authorization") != f"Bearer {stub.require_key}":
                    return self._reply(401, b'{"error": "invalid api key (stub)"}')
                try:
                    req = json.loads(body)
                    texts = req["input"] if isinstance(req["input"], list) else [req["input"]]
                except (ValueError, KeyError, TypeError):
                    return self._reply(400, b'{"error": "bad request"}')
                if stub.latency:
                    time.sleep(stub.latency)
                status = stub._decide(len(texts))
                if status == 503:
                    return self._reply(503, b'{"error": "service unavailable (stub)"}')
                if status == 413:
                    return self._reply(413, b'{"error": "payload too large (stub)"}')
                data = [{"object": "embedding", "index": i, "embedding": stub_vector(t, stub.dim)}
                        for i, t in enumerate(texts)]
                with stub._lock:
                    stub.texts_served.extend(texts)
                self._reply(200, json.dumps({"object": "list", "data": data, "model": req.get("model")}).encode())

            def log_message(self, *args):
                pass

        return Handler


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--dim", type=int, default=8)
    ap.add_argument("--latency", type=float, default=0.1)
    ap.add_argument("--fail-rate", type=float, default=0.0)
    ap.add_argument("--too-large-rate", type=float, default=0.0)
    args = ap.parse_args()
    srv = StubEmbedServer(dim=args.dim, latency=args.latency, fail_rate=args.fail_rate,
                          too_large_rate=args.too_large_rate, port=args.port)
    print(f"stub embedding server on {srv.url} (Ctrl-C to stop)", flush=True)
    try:
        srv._srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv._srv.server_close()
        print(f"served {len(srv.texts_served)} texts in {srv.n_requests} requests "
              f"({srv.n_503} x 503, {srv.n_413} x 413)")


if __name__ == "__main__":
    main()
