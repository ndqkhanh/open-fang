"""v5.0 — claude-mem MCP tool-name parity tests (memory.*)."""
from __future__ import annotations

from open_fang.kb.store import KBStore
from open_fang.mcp_server.server import MCPServer
from open_fang.memory.store import MemoryStore
from open_fang.models import Span


def _seed_memory(kb: KBStore, count: int = 3) -> list[str]:
    memory = MemoryStore(kb)
    ids = []
    for i in range(count):
        ids.append(
            memory.append(
                Span(
                    trace_id=f"t{i}",
                    node_id=f"n{i}",
                    kind="search.arxiv",  # type: ignore[arg-type]
                    started_at=float(i),
                    ended_at=float(i) + 0.1,
                    verdict="ok",  # type: ignore[arg-type]
                )
            )
        )
    return ids


def _server_with_kb() -> tuple[MCPServer, KBStore]:
    kb = KBStore(db_path=":memory:").open()
    return MCPServer(kb=kb), kb


def test_tools_list_now_includes_memory_triplet():
    srv, _ = _server_with_kb()
    resp = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    tool_names = sorted(t["name"] for t in resp["result"]["tools"])
    # v2.6 had 4 tools; v5.0 adds 3 memory.* tools for claude-mem parity.
    assert "memory.search" in tool_names
    assert "memory.timeline" in tool_names
    assert "memory.get_observations" in tool_names
    # v2.6 tools still present.
    assert "kb.search" in tool_names
    assert "skill.list" in tool_names


def test_memory_search_returns_newest_observations_for_empty_query():
    srv, kb = _server_with_kb()
    _seed_memory(kb, count=5)
    resp = srv.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "memory.search", "arguments": {"query": "", "limit": 3}},
        }
    )
    content = resp["result"]["content"][0]["text"]
    assert "search.arxiv" in content
    # Three observations returned (limit honored).
    assert len(content.splitlines()) == 3


def test_memory_timeline_paginates():
    srv, kb = _server_with_kb()
    _seed_memory(kb, count=5)
    resp = srv.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "memory.timeline", "arguments": {"offset": 2, "limit": 2}},
        }
    )
    content = resp["result"]["content"][0]["text"]
    # Tab-separated: id \t timestamp \t compact_summary
    assert len(content.splitlines()) == 2
    for line in content.splitlines():
        assert line.count("\t") == 2


def test_memory_get_observations_fetches_by_id():
    srv, kb = _server_with_kb()
    ids = _seed_memory(kb, count=2)
    resp = srv.handle(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "memory.get_observations",
                "arguments": {"ids": ids},
            },
        }
    )
    content = resp["result"]["content"][0]["text"]
    for obs_id in ids:
        assert f"=== {obs_id} ===" in content


def test_memory_get_observations_handles_missing_ids_gracefully():
    srv, _ = _server_with_kb()
    resp = srv.handle(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "memory.get_observations",
                "arguments": {"ids": ["does-not-exist"]},
            },
        }
    )
    assert resp["result"]["isError"] is False
    assert "(not found)" in resp["result"]["content"][0]["text"]


def test_memory_search_without_kb_returns_warning():
    srv = MCPServer(kb=None)
    resp = srv.handle(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "memory.search", "arguments": {"query": "x"}},
        }
    )
    assert "(no KB configured)" in resp["result"]["content"][0]["text"]
