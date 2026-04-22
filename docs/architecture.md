# OpenFang — Architecture (v2)

Canonical references: [../plan.md](../plan.md) (v1), [../v2-plan.md](../v2-plan.md) (v2). This file captures the big-picture view; detail lives in `blocks/*.md` and the subsystem docstrings.

## Pipeline (v2)

```
Brief + FANG.md + SkillRegistry
     │
     ▼
┌─────────────────────────────┐
│ Phase 1: DAGPlanner          │  (LLM; canonical fallback on invalid JSON)
└─────────────────────────────┘
     │ typed DAG
     ▼
┌─────────────────────────────┐
│ Phase 2: SchedulerEngine     │ (deterministic)
│  ├─ parking (permissions)    │
│  ├─ chaos (v2.5 fault inj)   │
│  ├─ retries (node-local)     │
│  ├─ kb.lookup → KBStore      │
│  └─ search.* → SourceRouter  │
└─────────────────────────────┘
     │ evidence[]
     ▼
┌─────────────────────────────┐
│ SynthesisWriter              │
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│ ClaimVerifier — 5 tiers (v2.4)                      │
│  1. Lexical          (free, pre-filter)             │
│  2. Mutation-robust  (warning — does not veto)      │
│  3. LLM judge        (JSON verdict contract)        │
│  4. Executable       (Vcode sandbox, quant claims)  │
│  5. Cross-channel    (metadata flag)                │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐     ┌─────────────────┐
│ CriticAgent (CoV)            │────▶│ RedTeamAgent    │ (v2.5)
└─────────────────────────────┘     └─────────────────┘
     │
     ▼
┌─────────────────────────────┐
│ KB promotion gate + edges    │ (v1.4 + v2.2)
└─────────────────────────────┘
     │
     ▼
   Report + PipelineResult
   (claims bound to evidence, faithfulness_ratio,
    activated_skills, Gnomon spans, trace_id)
```

## Key commitments

1. **Every claim is structurally bound to evidence IDs** — no prose citations.
2. **Verifier is a gate**, not a suggestion. `faithfulness_ratio < 0.90` blocks release.
3. **Deterministic scheduler over free-form ReAct** — fault locality at node granularity.
4. **Persona partition never compacted** — research preferences survive long sessions.
5. **SQLite+FTS5 for the KB in v1–v2** — local-first, zero ops. Revisit at >100k papers.
6. **Gnomon spans from day one** — telemetry attributes failures to primitives.
7. **Read-only external surface** (v2.6) — MCP exposes `skill.list / skill.get / kb.search / kb.paper` only; write operations stay internal.
8. **Security probes + chaos hooks are opt-in** (v2.5) — `OPENFANG_CHAOS_MODE=network_drop:0.2` flips fault injection; static detector is always on.

## Subsystems (v2)

- `planner/` — `DAGPlanner` + schema validator (cycles, dup IDs, missing deps) + replanner stub
- `scheduler/` — `SchedulerEngine` with parking / retries / chaos / cost router
- `sources/` — `SourceRouter` + `ArxivSource` / `S2Source` / `GithubSource` + `MockSource` + `MCPSpecSource` (v2.6)
- `extract/` — `ClaimExtractor` + PDF/LaTeX stubs
- `verify/` — `ClaimVerifier` (5 tiers) + `CriticAgent` (CoV) + `MutationProbe` (v2.4) + `ExecutableVerifier` (v2.4) + `RedTeamAgent` (v2.5)
- `synthesize/` — `SynthesisWriter` with structural evidence binding
- `kb/` — `KBStore` (SQLite+FTS5) + `EdgeExtractor` (v2.2) + `random_walk` + `promote_report` + `build_subgraph` (v2.3) + `DecontaminationScanner` (v2.7)
- `memory/` — `FANGLoader` + `WorkingBuffer` + `ContextAssembler`
- `permissions/` — `PermissionBridge` + `TokenRegistry` (session/once/pattern)
- `observe/` — Gnomon-shape `SpanRecorder`
- `eval/` — `pass_at_k` / `pass_pow_k` + `MultiHopBriefSynthesizer` (v2.2) + `parse_feed` (v2.7)
- `skills/` — ECC-format `SKILL.md` loader + registry + `TrajectoryExtractor` + `Diagnostician` + `EvolvingArena` (v2.1)
- `security/` — `PromptInjectionProbe` / `CitationPoisoningProbe` / `InstructionHidingProbe` / `AdversarialKBProbe` + `detect_static_attacks`
- `mcp_server/` — stdio JSON-RPC server with 4 read-only tools (v2.6)

## Extension points

- **New source**: subclass `SearchSource`, register in `SourceRouter`.
- **New verifier tier**: implement the tier class, inject into `ClaimVerifier` via constructor.
- **New node kind**: extend `NodeKind` in `models.py`, add a handler in `scheduler/engine.py`, add a fixture DAG.
- **New MCP tool**: add a `Tool(...)` entry to `TOOLS` in `mcp_server/server.py` — read-only by convention.
- **New specialist** (v3.2+): drop a `SPECIALIST.md` under `specialists/` (v4) with `stage`, `owned_skills`, `verifier_tiers`, `model_family_preference`.
- **New skill**: folder under `skills/` with a valid `SKILL.md`; `openfang skill list` picks it up.
