"""OpenFang CLI.

Subcommands:
    skill list         — list loaded skills (v2.0)
    mcp serve          — run the stdio MCP server exposing read-only skill + KB tools
    mcp import         — ingest an MCP manifest JSON as a KB paper
    trace validate     — validate a JSONL trajectory file against the Atropos schema
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from .kb.store import KBStore
from .mcp_server.server import MCPServer, run_stdio
from .skills.loader import SkillLoader
from .skills.registry import SkillRegistry
from .sources.mcp import MCPSpecSource
from .trace.export import validate_trajectory


def _cmd_skill_list(args: argparse.Namespace) -> int:
    registry = SkillRegistry.from_loader(SkillLoader())
    skills = registry.list()
    if not skills:
        print("no skills loaded", file=sys.stderr)
        return 1
    if args.json:
        payload = [
            {
                "name": s.name,
                "description": s.description,
                "origin": s.origin,
                "confidence": s.frontmatter.confidence,
                "path": str(s.path) if s.path else None,
            }
            for s in skills
        ]
        print(json.dumps(payload, indent=2))
        return 0
    for s in skills:
        tag = f"[{s.origin}]"
        suffix = (
            f" (confidence={s.frontmatter.confidence:.2f})"
            if s.frontmatter.confidence is not None
            else ""
        )
        print(f"{tag:<11} {s.name:<32} {s.description}{suffix}")
    return 0


def _open_kb() -> KBStore | None:
    path = os.environ.get("OPEN_FANG_DB_PATH", "").strip()
    if not path:
        return None
    return KBStore(db_path=Path(path)).open()


def _cmd_mcp_serve(args: argparse.Namespace) -> int:
    registry = SkillRegistry.from_loader(SkillLoader())
    kb = _open_kb()
    server = MCPServer(skill_registry=registry, kb=kb)
    run_stdio(server)
    return 0


def _cmd_mcp_import(args: argparse.Namespace) -> int:
    kb = _open_kb()
    if kb is None:
        print(
            "OPEN_FANG_DB_PATH not set — set it to the path of a writable SQLite file",
            file=sys.stderr,
        )
        return 2
    result = MCPSpecSource().ingest_file(Path(args.manifest), kb)
    print(
        f"ingested {result.paper_id} with {result.tool_count} tools",
        flush=True,
    )
    return 0


def _cmd_trace_validate(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        return 2
    n_lines = 0
    n_issues = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        n_lines += 1
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"line {n_lines}: invalid JSON — {exc}", file=sys.stderr)
            n_issues += 1
            continue
        issues = validate_trajectory(payload)
        if issues:
            n_issues += len(issues)
            for issue in issues:
                print(f"line {n_lines}: {issue}", file=sys.stderr)
    print(f"{n_lines} trajectories scanned; {n_issues} issue(s)")
    return 0 if n_issues == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openfang", description="OpenFang CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    skill = sub.add_parser("skill", help="Manage the skill library")
    skill_sub = skill.add_subparsers(dest="skill_command", required=True)
    skill_list = skill_sub.add_parser("list", help="List loaded skills")
    skill_list.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    skill_list.set_defaults(func=_cmd_skill_list)

    mcp = sub.add_parser("mcp", help="MCP server + manifest import")
    mcp_sub = mcp.add_subparsers(dest="mcp_command", required=True)
    mcp_serve = mcp_sub.add_parser(
        "serve", help="Run the stdio MCP server (read-only skill + KB tools)"
    )
    mcp_serve.set_defaults(func=_cmd_mcp_serve)
    mcp_import = mcp_sub.add_parser("import", help="Ingest an MCP manifest JSON into the KB")
    mcp_import.add_argument("manifest", help="Path to the MCP manifest JSON file")
    mcp_import.set_defaults(func=_cmd_mcp_import)

    trace = sub.add_parser("trace", help="Trajectory export (Atropos-compatible JSONL)")
    trace_sub = trace.add_subparsers(dest="trace_command", required=True)
    trace_validate = trace_sub.add_parser(
        "validate", help="Validate a JSONL file against the Atropos trajectory schema"
    )
    trace_validate.add_argument("path", help="Path to the JSONL trajectory file")
    trace_validate.set_defaults(func=_cmd_trace_validate)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
