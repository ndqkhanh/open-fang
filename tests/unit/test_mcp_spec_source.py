from __future__ import annotations

import json
from pathlib import Path

from open_fang.kb.store import KBStore
from open_fang.sources.mcp import MCPSpecSource


def _manifest() -> dict:
    return {
        "serverInfo": {"name": "example-mcp", "version": "0.1.0"},
        "description": "Example MCP server exposing two tools.",
        "tools": [
            {"name": "echo", "description": "Return the input."},
            {"name": "timestamp", "description": "Return the current UTC timestamp."},
        ],
    }


def test_to_evidence_maps_manifest_fields():
    ev = MCPSpecSource().to_evidence(_manifest())
    assert ev.source.kind == "mcp"
    assert ev.source.identifier == "mcp:example-mcp"
    assert "Example MCP server" in ev.content
    assert "echo" in ev.content
    assert ev.structured_data["tool_count"] == 2
    assert ev.structured_data["tool_names"] == ["echo", "timestamp"]


def test_ingest_manifest_upserts_paper_into_kb():
    kb = KBStore(db_path=":memory:").open()
    result = MCPSpecSource().ingest_manifest(_manifest(), kb)
    assert result.paper_id == "mcp:example-mcp"
    assert result.tool_count == 2
    assert kb.count_papers() == 1
    # Searching the MCP paper by its name returns it (FTS5).
    hits = kb.search("example MCP")
    assert hits
    assert hits[0].source.identifier == "mcp:example-mcp"


def test_ingest_file_reads_json_manifest(tmp_path: Path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(_manifest()), encoding="utf-8")
    kb = KBStore(db_path=":memory:").open()
    result = MCPSpecSource().ingest_file(path, kb)
    assert result.paper_id == "mcp:example-mcp"
    assert kb.get_paper("mcp:example-mcp") is not None


def test_manifest_without_tools_still_ingests():
    kb = KBStore(db_path=":memory:").open()
    manifest = {"serverInfo": {"name": "bare-mcp"}, "description": "", "tools": []}
    result = MCPSpecSource().ingest_manifest(manifest, kb)
    assert result.tool_count == 0
    assert kb.count_papers() == 1


def test_empty_manifest_uses_fallback_name():
    ev = MCPSpecSource().to_evidence({})
    assert ev.source.identifier == "mcp:unknown-mcp"
    assert ev.structured_data["tool_count"] == 0
