from __future__ import annotations

from open_fang.kb.store import KBStore
from open_fang.mcp_server.http import (
    RateLimiter,
    handle_http_rpc,
    http_mode_enabled,
    token_from_env,
)
from open_fang.mcp_server.server import MCPServer


def _server() -> MCPServer:
    kb = KBStore(db_path=":memory:").open()
    return MCPServer(skill_registry=None, kb=kb)


def test_valid_token_returns_jsonrpc_result():
    s = _server()
    result = handle_http_rpc(
        s,
        request_body={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        auth_header="Bearer secret-token",
        expected_token="secret-token",
    )
    assert result.status == 200
    assert result.body["id"] == 1
    assert result.body["result"]["serverInfo"]["name"] == "open-fang"


def test_wrong_token_returns_401():
    result = handle_http_rpc(
        _server(),
        request_body={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        auth_header="Bearer wrong",
        expected_token="secret-token",
    )
    assert result.status == 401


def test_missing_auth_header_returns_401():
    result = handle_http_rpc(
        _server(),
        request_body={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        auth_header=None,
        expected_token="secret-token",
    )
    assert result.status == 401


def test_malformed_auth_header_returns_401():
    result = handle_http_rpc(
        _server(),
        request_body={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        auth_header="Basic user:pass",
        expected_token="secret-token",
    )
    assert result.status == 401


def test_missing_expected_token_returns_500():
    result = handle_http_rpc(
        _server(),
        request_body={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        auth_header="Bearer anything",
        expected_token=None,
    )
    assert result.status == 500


def test_notification_returns_204():
    result = handle_http_rpc(
        _server(),
        request_body={"jsonrpc": "2.0", "method": "notifications/initialized"},
        auth_header="Bearer t",
        expected_token="t",
    )
    assert result.status == 204


def test_rate_limit_triggers_429():
    limiter = RateLimiter(requests_per_minute=3)
    base = 1000.0
    for i in range(3):
        # Feed monotonic time via the limiter directly for determinism.
        assert limiter.allow("t", now=base + i * 0.1) is True
    assert limiter.allow("t", now=base + 0.4) is False


def test_rate_limit_resets_after_window():
    limiter = RateLimiter(requests_per_minute=2)
    assert limiter.allow("t", now=0.0) is True
    assert limiter.allow("t", now=0.1) is True
    assert limiter.allow("t", now=0.2) is False
    # After 61 seconds, window is clear.
    assert limiter.allow("t", now=61.0) is True


def test_rate_limit_per_token_isolation():
    limiter = RateLimiter(requests_per_minute=1)
    assert limiter.allow("t1", now=0.0) is True
    assert limiter.allow("t2", now=0.0) is True
    assert limiter.allow("t1", now=0.0) is False
    assert limiter.allow("t2", now=0.0) is False


def test_http_mode_env_flag(monkeypatch):
    monkeypatch.delenv("OPEN_FANG_MCP_HTTP", raising=False)
    assert http_mode_enabled() is False
    monkeypatch.setenv("OPEN_FANG_MCP_HTTP", "1")
    assert http_mode_enabled() is True


def test_token_from_env(monkeypatch):
    monkeypatch.delenv("OPEN_FANG_MCP_TOKEN", raising=False)
    assert token_from_env() is None
    monkeypatch.setenv("OPEN_FANG_MCP_TOKEN", "secret")
    assert token_from_env() == "secret"
    monkeypatch.setenv("OPEN_FANG_MCP_TOKEN", "   ")
    assert token_from_env() is None
