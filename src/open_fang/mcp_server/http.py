"""Remote MCP over HTTP with Bearer auth (v8.6).

Pattern source: GBrain remote-MCP (HTTP + Bearer token auth).

Wire format is identical to stdio MCP (v2.6) — same JSON-RPC 2.0, same
tool names, same input schemas. The transport is POST /mcp/rpc with
`Authorization: Bearer <token>` + a 401 on missing/wrong token.

Opt-in: mounted only when `OPEN_FANG_MCP_HTTP=1` is set.
Per-token rate limit via a sliding-window counter.
"""
from __future__ import annotations

import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from .server import MCPServer

DEFAULT_RATE_LIMIT_PER_MIN = 100


@dataclass
class RateLimiter:
    requests_per_minute: int = DEFAULT_RATE_LIMIT_PER_MIN
    _windows: dict[str, deque] = field(default_factory=dict)

    def allow(self, token: str, *, now: float | None = None) -> bool:
        t = now if now is not None else time.monotonic()
        window = self._windows.setdefault(token, deque())
        # Evict entries older than 60s.
        while window and window[0] <= t - 60.0:
            window.popleft()
        if len(window) >= self.requests_per_minute:
            return False
        window.append(t)
        return True


@dataclass
class HTTPMCPResult:
    status: int
    body: dict[str, Any]


def handle_http_rpc(
    server: MCPServer,
    *,
    request_body: dict[str, Any],
    auth_header: str | None,
    expected_token: str | None,
    rate_limiter: RateLimiter | None = None,
) -> HTTPMCPResult:
    """Process one /mcp/rpc POST. Enforces Bearer auth + rate limit.

    Returns the outgoing (status, body) pair — transport-agnostic so tests
    can call this directly without mounting FastAPI.
    """
    # --- auth
    if not expected_token:
        # Server misconfigured — refuse to serve rather than running open.
        return HTTPMCPResult(
            status=500,
            body={"error": "server missing OPEN_FANG_MCP_TOKEN"},
        )
    if not auth_header or not auth_header.startswith("Bearer "):
        return HTTPMCPResult(status=401, body={"error": "missing bearer token"})
    token = auth_header[len("Bearer "):].strip()
    if token != expected_token:
        return HTTPMCPResult(status=401, body={"error": "invalid bearer token"})

    # --- rate limit
    limiter = rate_limiter or RateLimiter()
    if not limiter.allow(token):
        return HTTPMCPResult(status=429, body={"error": "rate limit exceeded"})

    # --- JSON-RPC dispatch — same code path as stdio.
    response = server.handle(request_body)
    if response is None:
        # Notifications have no response; HTTP returns 204.
        return HTTPMCPResult(status=204, body={})
    return HTTPMCPResult(status=200, body=response)


def http_mode_enabled() -> bool:
    return os.environ.get("OPEN_FANG_MCP_HTTP", "").strip() == "1"


def token_from_env() -> str | None:
    raw = os.environ.get("OPEN_FANG_MCP_TOKEN", "").strip()
    return raw or None
