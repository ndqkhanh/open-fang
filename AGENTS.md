# AGENTS.md — OpenFang

Universal entry point. Every agent harness (Claude Code, Cursor, Codex, OpenCode, Antigravity, Gemini CLI) reads this file at project open. Keep it under 200 lines; longer content lives in [README.md](README.md) and [plan.md](plan.md).

## What OpenFang is

An autonomous AI research agent specialized for **AI / AI Agents / Agentic AI / Harness Engineering** literature. v2 ships a DAG-teams planner + scheduler, three-tier memory with a persona partition, SQLite+FTS5 knowledge base with a weighted citation graph, 5-tier hardened verifier (lexical → mutation → LLM-judge → executable → cross-channel), security probes + chaos hooks + red-team, 5-skill library with evolving-arena extraction, and a read-only MCP server.

## How to invoke

Local dev:

```bash
make install           # venv + harness_core (editable) + deps
make test              # pytest — 262 tests + 1 network-deselected
make lint              # ruff
make run               # uvicorn on :8010
```

CLI surface:

```bash
openfang skill list                            # list the skill library
openfang skill list --json                     # same, machine-readable
openfang mcp serve                             # stdio MCP server (read-only)
openfang mcp import <manifest.json>            # ingest an MCP manifest as a KB paper
```

HTTP surface (when `make run`):

```
GET  /healthz
POST /v1/research                     # Brief → Report
POST /v1/permissions/approve          # grant session/once/pattern tokens
GET  /v1/kb/papers                    # list all KB papers (requires OPEN_FANG_DB_PATH)
GET  /v1/kb/paper/{id}                # paper detail + citation edges
GET  /v1/kb/graph?seed=|query=&depth= # BFS subgraph for the /viewer/
GET  /viewer/                         # read-only cytoscape.js graph viewer
```

MCP tools (when `openfang mcp serve` runs as a stdio server):

- `skill.list` — list loaded skills
- `skill.get` — fetch one SKILL.md by name
- `kb.search` — FTS5 search over KB
- `kb.paper` — fetch one paper with edges

**Read-only by design.** No write surface is exposed over MCP. `kb.promote` stays internal to the pipeline.

## Skills shipped (5 curated, ECC-format)

Under [skills/](skills/):

| Skill | Purpose |
| --- | --- |
| `claim-localization` | find the sentence in evidence that supports a claim |
| `citation-extraction` | extract references from a paper's body |
| `counter-example-generation` | generate mutants for Tier-2 verifier |
| `reproduction-script` | emit Python assertions for Tier-4 executable verification |
| `peer-review` | structured critique of a finished report |

Resolution order: `skills/` (curated) → `~/.openfang/skills/{learned, imported, evolved}/`.

## Persona

Edit [FANG.md](FANG.md) — size-capped, never-compacted, version-controlled. Loaded fresh each session. Used by the planner + synthesis writer to shape output (citation style, evidence bar, preferred venues).

## Principles (from Andrej Karpathy's agent-coding guidance)

1. **Think Before Coding** — plan the DAG first, not prose first.
2. **Simplicity First** — one claim per evidence; no abstractions until there are three call sites.
3. **Surgical Changes** — every edit targets the minimum failing scope.
4. **Goal-Driven Execution** — every node has a verifiable output; every verifier has a floor.

## Contributing a skill

- Add a folder under [skills/](skills/) with a `SKILL.md`.
- Frontmatter: `name`, `description`, `origin` (must be `curated` for repo-shipped), optional `confidence`.
- Six sections: Overview / When to Activate / Concepts / Code Examples / Anti-Patterns / Best Practices.
- Run `openfang skill list` — your skill should appear.

## Status

v2.7 release. 262/262 tests green + 1 network-deselected. Ruff clean. Docker compose ships.

See [plan.md](plan.md), [v2-plan.md](v2-plan.md), [v3-plan.md](v3-plan.md), [v4-plan.md](v4-plan.md) for the roadmap.
