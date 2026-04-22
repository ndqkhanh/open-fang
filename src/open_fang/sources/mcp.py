"""MCPSpecSource: ingest an MCP server's manifest as a KB paper.

Reads a manifest JSON (the `initialize` + `tools/list` response shape from an
MCP server) and produces an `Evidence` record treating the MCP server as a
first-class KB citizen — "tool-paper" entries per plan.md §5 W5 inspired by
arxiv:2604.18292 (Agent-World).

Manifest shape (minimum):
    {
      "serverInfo": {"name": "...", "version": "..."},
      "description": "...",                     # optional
      "tools": [{"name": "...", "description": "..."}, ...]
    }
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..kb.store import KBStore
from ..models import Evidence, SourceRef


@dataclass
class MCPIngestResult:
    paper_id: str
    tool_count: int


class MCPSpecSource:
    """Turn an MCP manifest into a `cites`-less `Evidence` row for the KB."""

    def to_evidence(self, manifest: dict[str, Any]) -> Evidence:
        server = manifest.get("serverInfo") or {}
        name = str(server.get("name") or "unknown-mcp")
        version = str(server.get("version") or "")
        description = str(manifest.get("description") or "")
        tools = manifest.get("tools") or []

        tool_summary = "\n".join(
            f"- {t.get('name', '<unnamed>')}: {t.get('description', '')}"
            for t in tools
        )
        abstract = (
            f"MCP server {name!r} (v{version}). "
            f"{description}\n\nTools:\n{tool_summary}"
        ).strip()

        return Evidence(
            source=SourceRef(
                kind="mcp",
                identifier=f"mcp:{name}",
                title=f"MCP: {name}",
                authors=[],
                published_at=None,
            ),
            content=abstract,
            channel="manifest",
            relevance=1.0,
            structured_data={
                "mcp_name": name,
                "mcp_version": version,
                "tool_count": len(tools),
                "tool_names": [str(t.get("name", "")) for t in tools],
            },
        )

    def ingest_file(self, path: Path | str, kb: KBStore) -> MCPIngestResult:
        import json

        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
        return self.ingest_manifest(manifest, kb)

    def ingest_manifest(self, manifest: dict[str, Any], kb: KBStore) -> MCPIngestResult:
        ev = self.to_evidence(manifest)
        paper_id = kb.upsert_paper(ev.source, abstract=ev.content)
        return MCPIngestResult(
            paper_id=paper_id,
            tool_count=int(ev.structured_data.get("tool_count", 0)),
        )
