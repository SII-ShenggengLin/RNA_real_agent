#!/usr/bin/env python3
"""Round-robin reverse proxy for the ODesign resident replica fleet.

Infrastructure-only accelerator (Exp 30, 2026-09-05, user-directed): the
production tool default ``http://127.0.0.1:8012/design/from-json`` is a
single endpoint, so concurrent form sessions would serialize on one
replica. This proxy listens on the legacy port (default 8012) and spreads
``POST /design/from-json`` across the resident replicas round-robin;
``GET /health`` is forwarded to the next live backend. Request and
response bodies pass through byte-identically — the replicas themselves
are the byte-identical resident services already registered in the
platform notes (~22 s/request vs ~90 s subprocess path).

Backends: comma-separated URLs in ``ODESIGN_PROXY_BACKENDS`` (default the
six resident replicas on ports 18112-18117, two per GPU across GPUs 0/1/2).

Usage:
    python microservices/odesign_service/roundrobin_proxy.py [port]
"""
from __future__ import annotations

import itertools
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import requests

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8012
BACKENDS = [
    b.strip().rstrip("/")
    for b in os.environ.get(
        "ODESIGN_PROXY_BACKENDS",
        ",".join(f"http://127.0.0.1:{p}" for p in range(18112, 18118)),
    ).split(",")
    if b.strip()
]
# Per-request timeout: generous connect timeout, wrapper-level read
# timeout (wrapper uses max(21600, timeout_seconds + 600)).
TIMEOUT = (10, 21600)

_cycle = itertools.cycle(range(len(BACKENDS)))
_lock = threading.Lock()


def next_backend(skip: int = -1) -> str | None:
    with _lock:
        for _ in range(len(BACKENDS)):
            idx = next(_cycle)
            if idx != skip:
                return BACKENDS[idx]
    return None


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        sys.stdout.write(f"[proxy] {self.address_string()} {fmt % args}\n")
        sys.stdout.flush()

    def _relay(self, resp: requests.Response) -> None:
        body = resp.content
        self.send_response(resp.status_code)
        for key, value in resp.headers.items():
            if key.lower() in {"content-length", "transfer-encoding",
                               "connection", "content-encoding"}:
                continue
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/health":
            self.send_error(404, "not fronted by proxy")
            return
        skip = -1
        for _ in range(len(BACKENDS)):
            backend = next_backend(skip)
            if backend is None:
                break
            try:
                resp = requests.get(f"{backend}/health", timeout=5)
                self._relay(resp)
                return
            except requests.RequestException:
                skip = BACKENDS.index(backend)
        self.send_error(502, "all backends down")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/design/from-json":
            self.send_error(404, "not fronted by proxy")
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        skip = -1
        for _ in range(len(BACKENDS)):
            backend = next_backend(skip)
            if backend is None:
                break
            try:
                resp = requests.post(
                    f"{backend}/design/from-json",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    timeout=TIMEOUT,
                )
                self._relay(resp)
                return
            except requests.RequestException as exc:
                self.log_message("backend %s failed: %r", backend, exc)
                skip = BACKENDS.index(backend)
        self.send_error(502, "all backends failed")


def main() -> int:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), ProxyHandler)
    print(f"[proxy] listening on :{PORT} -> {BACKENDS}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
