"""MCPServer: JSON-RPC 2.0 + Model Context Protocol (2024-11-05) over stdio.

Minimal stdlib-only server that exposes read-only skill + KB tools. The
handler returns a response dict for every request dict; `run_stdio` is a
thin loop that reads newline-delimited JSON from stdin and writes to stdout.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable

from ..kb.store import KBStore
from ..memory.store import MemoryStore
from ..skills.registry import SkillRegistry

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "open-fang", "version": "0.1.0"}


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict, MCPServer], str]


def _tool_skill_list(_args: dict, srv: MCPServer) -> str:
    if srv.skill_registry is None:
        return "(no skill registry configured)"
    skills = srv.skill_registry.list()
    lines = [
        f"[{s.origin}] {s.name} — {s.description}"
        for s in skills
    ]
    return "\n".join(lines) if lines else "(no skills loaded)"


def _tool_skill_get(args: dict, srv: MCPServer) -> str:
    if srv.skill_registry is None:
        return "(no skill registry configured)"
    name = str(args.get("name", ""))
    skill = srv.skill_registry.get(name)
    if skill is None:
        return f"(skill not found: {name!r})"
    return skill.raw_markdown or skill.overview


def _tool_kb_search(args: dict, srv: MCPServer) -> str:
    if srv.kb is None:
        return "(no KB configured)"
    query = str(args.get("query", ""))
    limit = int(args.get("limit", 5))
    hits = srv.kb.search(query, limit=limit)
    if not hits:
        return "(no results)"
    return "\n".join(
        f"{h.source.identifier}\t{h.source.title}"
        for h in hits
    )


def _tool_kb_paper(args: dict, srv: MCPServer) -> str:
    if srv.kb is None:
        return "(no KB configured)"
    paper_id = str(args.get("id", ""))
    ev = srv.kb.get_paper(paper_id)
    if ev is None:
        return f"(paper not found: {paper_id!r})"
    edges = srv.kb.list_edges(paper_id)
    edge_lines = [f"{src} -[{kind}]-> {dst}" for src, dst, kind in edges]
    return "\n".join(
        [
            f"id: {ev.source.identifier}",
            f"title: {ev.source.title}",
            f"authors: {', '.join(ev.source.authors)}",
            f"published_at: {ev.source.published_at or ''}",
            "",
            "abstract:",
            ev.content,
            "",
            "edges:",
            *edge_lines,
        ]
    )


def _tool_memory_search(args: dict, srv: MCPServer) -> str:
    """v5.0 — FTS5-over-observations search; claude-mem tool-name parity."""
    if srv.kb is None:
        return "(no KB configured)"
    memory = MemoryStore(srv.kb)
    query = str(args.get("query", "")).strip()
    limit = int(args.get("limit", 10))
    if not query:
        # Empty query: return the newest compact index entries.
        return "\n".join(memory.compact_index(limit=limit)) or "(no observations)"
    # MemoryStore doesn't yet index observations in FTS5; token-match the
    # compact index as a v5.0 MVP. (v5.1 can promote to a real FTS5 mirror.)
    q_tokens = {t.lower() for t in query.split() if len(t) > 2}
    hits = []
    for line in memory.compact_index(limit=200):
        if any(tok in line.lower() for tok in q_tokens):
            hits.append(line)
            if len(hits) >= limit:
                break
    return "\n".join(hits) or "(no match)"


def _tool_memory_timeline(args: dict, srv: MCPServer) -> str:
    """v5.0 — paginated timeline; returns summary + id per entry."""
    if srv.kb is None:
        return "(no KB configured)"
    memory = MemoryStore(srv.kb)
    offset = int(args.get("offset", 0))
    limit = int(args.get("limit", 20))
    observations = memory.timeline(offset=offset, limit=limit)
    if not observations:
        return "(no observations)"
    return "\n".join(
        f"{o.id}\t{o.timestamp}\t{o.compact_summary}" for o in observations
    )


def _tool_memory_get_observations(args: dict, srv: MCPServer) -> str:
    """v5.0 — fetch full details for a list of observation ids."""
    if srv.kb is None:
        return "(no KB configured)"
    memory = MemoryStore(srv.kb)
    ids = args.get("ids", [])
    if isinstance(ids, str):
        ids = [ids]
    if not ids:
        return "(no ids provided)"
    out: list[str] = []
    for oid in ids:
        obs = memory.get_observation(str(oid))
        if obs is None:
            out.append(f"{oid}\t(not found)")
            continue
        out.append(
            f"=== {obs.id} ===\n"
            f"timestamp: {obs.timestamp}\n"
            f"kind: {obs.node_kind}\n"
            f"verdict: {obs.verdict}\n"
            f"summary: {obs.compact_summary}\n"
            f"detail: {obs.detail_summary}\n"
        )
    return "\n".join(out)


TOOLS: list[Tool] = [
    Tool(
        name="skill.list",
        description="List every skill loaded by the OpenFang registry.",
        input_schema={"type": "object", "properties": {}, "required": []},
        handler=_tool_skill_list,
    ),
    Tool(
        name="skill.get",
        description="Return the raw SKILL.md markdown for one skill by name.",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        handler=_tool_skill_get,
    ),
    Tool(
        name="kb.search",
        description="FTS5 search over the OpenFang knowledge base. Returns id+title pairs.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
            },
            "required": ["query"],
        },
        handler=_tool_kb_search,
    ),
    Tool(
        name="kb.paper",
        description="Fetch one KB paper by id with its citation-graph edges.",
        input_schema={
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
        handler=_tool_kb_paper,
    ),
    Tool(
        name="memory.search",
        description="v5.0 — Search over the OpenFang memory observations (claude-mem tool-name parity).",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
            },
            "required": ["query"],
        },
        handler=_tool_memory_search,
    ),
    Tool(
        name="memory.timeline",
        description="v5.0 — Paginated timeline of OpenFang memory observations.",
        input_schema={
            "type": "object",
            "properties": {
                "offset": {"type": "integer", "minimum": 0, "default": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 20},
            },
            "required": [],
        },
        handler=_tool_memory_timeline,
    ),
    Tool(
        name="memory.get_observations",
        description="v5.0 — Fetch full details for a list of observation ids.",
        input_schema={
            "type": "object",
            "properties": {
                "ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["ids"],
        },
        handler=_tool_memory_get_observations,
    ),
]


class MCPServer:
    def __init__(
        self,
        *,
        skill_registry: SkillRegistry | None = None,
        kb: KBStore | None = None,
        tools: list[Tool] | None = None,
    ) -> None:
        self.skill_registry = skill_registry
        self.kb = kb
        self.tools = tools or list(TOOLS)
        self._initialized = False

    def handle(self, msg: dict) -> dict | None:
        """Produce a response dict for a request dict. Returns None for notifications."""
        rpc_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params") or {}

        if method == "initialize":
            self._initialized = True
            return _ok(rpc_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            })

        if method == "notifications/initialized":
            # Notification — no response per JSON-RPC 2.0.
            return None

        if method == "tools/list":
            return _ok(rpc_id, {
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.input_schema,
                    }
                    for t in self.tools
                ]
            })

        if method == "tools/call":
            name = str(params.get("name", ""))
            args = dict(params.get("arguments") or {})
            tool = next((t for t in self.tools if t.name == name), None)
            if tool is None:
                return _err(rpc_id, -32602, f"unknown tool: {name!r}")
            try:
                text = tool.handler(args, self)
            except Exception as exc:  # noqa: BLE001
                return _ok(rpc_id, {
                    "content": [{"type": "text", "text": f"error: {exc}"}],
                    "isError": True,
                })
            return _ok(rpc_id, {
                "content": [{"type": "text", "text": text}],
                "isError": False,
            })

        return _err(rpc_id, -32601, f"method not found: {method!r}")


def run_stdio(
    server: MCPServer,
    *,
    input_stream: Iterable[str] | None = None,
    output_write: Callable[[str], Any] | None = None,
) -> None:
    """Blocking stdio loop. Reads newline-delimited JSON; writes same format."""
    if input_stream is None:
        input_stream = sys.stdin
    if output_write is None:
        def output_write(s: str) -> None:
            sys.stdout.write(s)
            sys.stdout.write("\n")
            sys.stdout.flush()
    for line in input_stream:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            output_write(json.dumps(_err(None, -32700, "parse error")))
            continue
        resp = server.handle(msg)
        if resp is not None:
            output_write(json.dumps(resp))


def _ok(rpc_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def _err(rpc_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}
