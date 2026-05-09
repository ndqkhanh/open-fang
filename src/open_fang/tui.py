"""OpenFang TUI — knowledge base + skills + MCP front door.

Wires the harness-tui shell with OpenFang's domain commands. Without an
HTTP daemon (Phase 2 work), uses MockTransport for streaming demos and
delegates real work to in-process registries via slash commands.
"""
from __future__ import annotations

import os
from typing import Optional

import click
from harness_tui import HarnessApp, ProjectConfig
from harness_tui.commands.registry import register_command
from harness_tui.transport import HTTPTransport, MockTransport

from .tui_theme import openfang_theme


@register_command(name="skill", description="List or inspect skills",
                  category="OpenFang")
async def cmd_skill(app, args: str) -> None:  # type: ignore[no-untyped-def]
    if args.startswith("list") or not args:
        try:
            from .skills.loader import SkillLoader
            from .skills.registry import SkillRegistry

            registry = SkillRegistry.from_loader(SkillLoader())
            skills = registry.list()
            body = "\n".join(
                f"  · {s.name:<28} {s.description[:60]}" for s in skills
            ) or "(no skills loaded)"
            app.shell.chat_log.write_system("skills:\n" + body)
        except Exception as exc:
            app.shell.chat_log.write_system(f"skill list: error — {exc}")
    else:
        app.shell.chat_log.write_system("usage: /skill list")


@register_command(name="kb", description="Knowledge base search (mock)",
                  category="OpenFang")
async def cmd_kb(app, args: str) -> None:  # type: ignore[no-untyped-def]
    if args.startswith("search "):
        q = args[7:].strip()
        app.shell.chat_log.write_system(f"kb search: {q!r} → see KBStore")
    else:
        app.shell.chat_log.write_system("usage: /kb search <query>")


@register_command(name="mcp", description="List MCP server config",
                  category="OpenFang")
async def cmd_mcp(app, _: str) -> None:  # type: ignore[no-untyped-def]
    app.shell.chat_log.write_system("mcp: stdio server available via `openfang mcp serve`")


@register_command(name="trace", description="Validate a JSONL trajectory file",
                  category="OpenFang")
async def cmd_trace(app, args: str) -> None:  # type: ignore[no-untyped-def]
    path = args.strip()
    if not path:
        app.shell.chat_log.write_system("usage: /trace <jsonl-file>")
        return
    try:
        from .trace.export import validate_trajectory
        import json
        from pathlib import Path

        n_lines = 0
        n_issues = 0
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            n_lines += 1
            try:
                payload = json.loads(line)
                issues = validate_trajectory(payload)
                n_issues += len(issues)
            except json.JSONDecodeError:
                n_issues += 1
        app.shell.chat_log.write_system(
            f"trace: {n_lines} trajectories scanned · {n_issues} issue(s)"
        )
    except Exception as exc:
        app.shell.chat_log.write_system(f"trace: error — {exc}")


@click.command()
@click.option("--url", default=None, help="FastAPI backend URL (optional).")
@click.option("--mock", is_flag=True, default=True, help="Use MockTransport (default).")
@click.option("--serve", is_flag=True,
              help="Run the TUI in a browser via textual-serve.")
@click.option("--port", type=int, default=8000, help="Web mode port (with --serve).")
@click.option("--host", default="127.0.0.1", help="Web mode host (with --serve).")
def main(url: Optional[str], mock: bool, serve: bool, port: int, host: str) -> None:
    """Open the OpenFang TUI."""
    if serve:
        from harness_tui.serve import serve_app, make_module_command

        flags = []
        if mock:
            flags.append("--mock")
        if url:
            flags.append(f"--url {url}")
        serve_app(
            command=make_module_command("open_fang.tui", " ".join(flags)),
            host=host, port=port,
            title="open-fang",
        )
        return
    if url and not mock:
        transport = HTTPTransport(url)
    else:
        transport = MockTransport()
    cfg = ProjectConfig(
        name="open-fang",
        description="Autonomous AI research agent",
        theme=openfang_theme(),
        transport=transport,
        model=os.environ.get("OPENFANG_MODEL", "auto"),
    )
    app = HarnessApp(cfg)
    app.run()
    summary = getattr(app, "last_exit_summary", None)
    if summary:
        click.echo(summary.render())


if __name__ == "__main__":  # pragma: no cover
    main()
