# OpenFang

🌐 **[Live demo & project page](https://ndqkhanh.github.io/open-fang/)** — landing page + sample citation-graph viewer (no API required).

Autonomous AI research agent specialized for **AI / AI Agents / Agentic AI / Harness Engineering** literature.

Built TDD-first. DAG Teams orchestration (Phase-1 LLM planner → Phase-2 deterministic scheduler), three-tier progressive-disclosure memory, SQLite+FTS5 KB with weighted citation graph + multi-hop synthesis, hardened 5-tier verifier (lexical → mutation → LLM-judge → executable → cross-channel) with 3-mode cross-model verification, 9-specialist research cohort with optional subprocess isolation, security probes + chaos hooks + red-team, 7-tool MCP server with agentskills.io-compliant skills and claude-mem tool-name parity, Atropos-compatible trajectory export, opt-in weekly feed cron, and multica runtime adapter.

## Status

**v8 — released. 612 tests green + 1 network-deselected, ruff clean.**

| Release | What landed | Tests |
| --- | --- | --- |
| v1.0–v1.7 | DAG scaffold + 5-tier pipeline + 20-brief eval + Docker | 129 |
| v2.0 | 5 curated skills (ECC `SKILL.md`) + CLI | 153 |
| v2.1 | `TrajectoryExtractor` + `Diagnostician` + `EvolvingArena` | 167 |
| v2.2 | Edge extractor + weighted walk + multi-hop synthesizer | 181 |
| v2.3 | `GET /v1/kb/graph` + cytoscape viewer | 200 |
| v2.4 | Tier-2 `MutationProbe` + Tier-4 `ExecutableVerifier` | 224 |
| v2.5 | 4 security probes + chaos hooks + red-team | 245 |
| v2.6 | stdio MCP server + `MCPSpecSource` | 262 |
| v2.7 | AGENTS.md + decontamination + 50-brief corpus | 305 |
| v3.0 | agentskills.io schema alignment + `validate_skill()` | 320 |
| v3.1 | Progressive-disclosure memory (3 tiers) + ≥5× token reduction | 341 |
| v3.2 | Supervisor + 5 specialists + `/v1/supervisor/status` | 361 |
| v3.3 | Trajectory export (Atropos-compatible JSONL) | 368 |
| v4.0 | 9-specialist cohort (+ ResearchDirector, Methodologist, ThreatModeler, Publisher) | 380 |
| v4.1 | Claim-kind router (quant/qual/citation/methodological) | 391 |
| v4.2 | Three-mode cross-model verification (review/adversarial/consultation) | 398 |
| v4.3 | `IsolatedSupervisor` (subprocess per specialist, opt-in) | 402 |
| v4.4 | Stage labels on Gnomon spans | 402 |
| v5.0 | claude-mem MCP tool-name parity (`memory.*`) | 408 |
| v5.1 | Skill tree hierarchy (Corpus2Skill-inspired) | 415 |
| v5.4 | Opt-in weekly feed cron | 419 |
| v5.5+v5.6 | Multica runtime adapter + release | 425 |
| v6.0 | **HAFC-lite primitive-level failure attribution** (12 primitives, rules-first) | 437 |
| v6.1 | ReBalance confidence-steered halt (`ConfidenceMonitor`) | 444 |
| v6.2 | Tier 4.5 symbolic claim-number verifier (catches "claimed 10×, actual 5×") | 454 |
| v6.3 | Native arxiv / GitHub / HuggingFace adapters (BibTeX + PwC + HF model lineage) | 466 |
| v6.4 | Chaos × HAFC fragility-matrix scanner | 471 |
| v6.5 | OpenFang self-research loop (researches its own plan files) | 478 |
| v6.6 | v6 release | 478 |
| v7.0 | **Tool-output sandbox** (Context Mode pattern) — FTS5-indexed payload deferral | 491 |
| v7.1 | Hybrid search + dense embeddings + RRF + optional reranker | 507 |
| v7.2 | Degradation detector (7 signals, S–F grades) + loop detector | 514 |
| v7.3 | Bayesian validity + contradiction detection | 522 |
| v7.4 | Delta-mode for source re-reads | 529 |
| v7.5 | Merkle-tree incremental indexing | 538 |
| v7.6 | Caveman-style output compression (standard/terse/ultra) | 547 |
| v7.7 | v7 release | 547 |
| v8.0 | **Zero-LLM self-wiring** — regex citation + author-year edge inference | 555 |
| v8.1 | Typed-edge cascade rules (depth-1, 4 rules) | 563 |
| v8.2 | Entity expansion (authors / affiliations / techniques / benchmarks) | 574 |
| v8.3 | Stale-link reconciler (preserves manual edges) | 580 |
| v8.4 | Backlink-boosted ranking | 587 |
| v8.5 | BrainBench-analog graph metrics (Precision@5 / Recall@5 / Graph-F1) | 601 |
| v8.6 | Remote MCP with Bearer auth + rate limit | 612 |
| **v8.7** | **v8 release** | **612** |
| **v6.6** | **Release v6** | **478** |

## Quickstart

```bash
make install        # venv + harness_core + deps
make test           # 478 tests + 1 network-deselected
make lint           # ruff
make run            # uvicorn on :8010
```

CLI:

```bash
openfang skill list
openfang mcp serve                      # stdio MCP server (7 read-only tools)
openfang mcp import manifest.json
openfang trace validate trajectories.jsonl
```

HTTP surface:

```text
GET  /healthz
POST /v1/research
POST /v1/permissions/approve
GET  /v1/kb/{papers,paper/{id},graph}
GET  /v1/memory/{timeline,observation/{id}}
GET  /v1/supervisor/status
GET  /viewer/                            # cytoscape.js graph viewer
```

MCP tools (7 read-only):

- `skill.list` / `skill.get`
- `kb.search` / `kb.paper`
- `memory.search` / `memory.timeline` / `memory.get_observations` — **claude-mem parity**

Ecosystem adapters:

- **Hermes Agent** — agentskills.io-compliant skills; Atropos-compatible trajectory export.
- **claude-mem** — drop-in MCP tool-name parity on `memory.*`.
- **multica** — install as a multica agent runtime via `MulticaAdapter`; handles full task-assignment lifecycle.

## Env flags

```bash
ANTHROPIC_API_KEY=...
HARNESS_LLM_MODEL=claude-3-5-sonnet-latest
OPEN_FANG_DB_PATH=/data/open_fang.db
OPEN_FANG_SUPERVISOR_MODE=isolated           # v4.3 subprocess supervision
OPEN_FANG_CHAOS_MODE=network_drop:0.2        # v2.5 fault injection
OPEN_FANG_FEED_CRON=1                        # v5.4 weekly puller
OPEN_FANG_FEED_INTERVAL_HOURS=168
OPEN_FANG_FEED_MAX_IMPORTS=20
```

## SLOs (gated in CI)

| Metric | Floor | Enforced by |
| --- | --- | --- |
| Aggregate + per-brief faithfulness (50 briefs) | ≥ 0.90 | `test_eval_corpus.py` |
| Per-brief Pass@5, aggregate Pass^5 | ≥ 0.70 | same |
| 5-paper faithfulness | ≥ 0.90 | `test_five_paper_faithfulness.py` |
| Security catch rate (10 adversarial) | ≥ 0.80 | `test_security_corpus.py` |
| Mutation resistance | ≥ 0.85 | `test_mutation_resistance.py` |
| Progressive-disclosure token reduction | ≥ 5× | `test_progressive_token_reduction.py` |

## Layout

See [AGENTS.md](AGENTS.md) for the universal entry point. Plan stack:
[plan.md](plan.md) (v1) → [v2-plan.md](v2-plan.md) → [v3-plan.md](v3-plan.md) → [v4-plan.md](v4-plan.md) → [v5-plan.md](v5-plan.md) → [v6-plan.md](v6-plan.md).

## License

MIT.
