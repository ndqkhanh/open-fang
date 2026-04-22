from __future__ import annotations

import json

from open_fang.kb.store import KBStore
from open_fang.mcp_server.server import MCPServer, run_stdio
from open_fang.models import SourceRef
from open_fang.skills.loader import SkillLoader
from open_fang.skills.registry import SkillRegistry


def _server() -> MCPServer:
    kb = KBStore(db_path=":memory:").open()
    kb.upsert_paper(
        SourceRef(kind="arxiv", identifier="arxiv:rewoo", title="ReWOO", authors=["X"]),
        abstract="ReWOO decouples reasoning from observations.",
    )
    registry = SkillRegistry.from_loader(SkillLoader())
    return MCPServer(skill_registry=registry, kb=kb)


def test_initialize_returns_server_info():
    resp = _server().handle(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "open-fang"
    assert "protocolVersion" in resp["result"]


def test_initialized_notification_returns_none():
    """JSON-RPC 2.0 notifications have no id and no response."""
    resp = _server().handle(
        {"jsonrpc": "2.0", "method": "notifications/initialized"}
    )
    assert resp is None


def test_tools_list_returns_seven_read_only_tools():
    """v2.6 shipped 4; v5.0 added 3 memory.* tools for claude-mem parity."""
    resp = _server().handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tool_names = sorted(t["name"] for t in resp["result"]["tools"])
    assert tool_names == [
        "kb.paper",
        "kb.search",
        "memory.get_observations",
        "memory.search",
        "memory.timeline",
        "skill.get",
        "skill.list",
    ]
    for t in resp["result"]["tools"]:
        assert "inputSchema" in t
        assert "description" in t


def test_tools_call_skill_list_returns_curated_skills():
    resp = _server().handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "skill.list", "arguments": {}},
        }
    )
    content = resp["result"]["content"][0]["text"]
    assert resp["result"]["isError"] is False
    assert "citation-extraction" in content
    assert "claim-localization" in content


def test_tools_call_kb_search_returns_hit():
    resp = _server().handle(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "kb.search", "arguments": {"query": "rewoo", "limit": 5}},
        }
    )
    content = resp["result"]["content"][0]["text"]
    assert "arxiv:rewoo" in content


def test_tools_call_kb_paper_returns_detail():
    resp = _server().handle(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "kb.paper", "arguments": {"id": "arxiv:rewoo"}},
        }
    )
    content = resp["result"]["content"][0]["text"]
    assert "title: ReWOO" in content
    assert "decouples" in content


def test_tools_call_unknown_tool_returns_error():
    resp = _server().handle(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "kb.mutate", "arguments": {}},
        }
    )
    assert "error" in resp
    assert resp["error"]["code"] == -32602


def test_unknown_method_returns_method_not_found():
    resp = _server().handle({"jsonrpc": "2.0", "id": 7, "method": "resources/list"})
    assert resp["error"]["code"] == -32601


def test_missing_registry_does_not_crash_skill_tools():
    server = MCPServer(skill_registry=None, kb=None)
    resp = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "skill.list", "arguments": {}},
        }
    )
    assert resp["result"]["isError"] is False
    assert "(no skill registry configured)" in resp["result"]["content"][0]["text"]


def test_run_stdio_echoes_each_line():
    """The stdio loop reads newline-delimited JSON and writes responses."""
    server = _server()
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    input_iter = iter([json.dumps(r) + "\n" for r in requests])
    written: list[str] = []
    run_stdio(server, input_stream=input_iter, output_write=written.append)
    parsed = [json.loads(line) for line in written]
    assert len(parsed) == 2
    assert parsed[0]["id"] == 1
    assert "tools" in parsed[1]["result"]
