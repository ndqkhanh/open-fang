"""OpenFang MCP server — read-only skill + KB tools exposed over stdio JSON-RPC.

Tools (v2.6):
    skill.list     — list loaded skills
    skill.get      — fetch one SKILL.md by name
    kb.search      — FTS5 search over papers
    kb.paper       — fetch one paper by id + incident edges

Per plan.md §10 risks, write tools (e.g., kb.promote) stay internal — only
read-only surface is exposed externally.
"""
from .server import TOOLS, MCPServer, run_stdio

__all__ = ["MCPServer", "TOOLS", "run_stdio"]
