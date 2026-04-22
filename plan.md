# OpenFang — TDD-First Autonomous AI Research Assistant

## 1. Context

OpenFang is a new project under `/Users/kane.nguyendinhquangkhanh/Downloads/Explore/research/harness-engineering/projects/open-fang/`, sibling to `atlas-research/`, `orion-code/`, `vertex-eval/`, etc.

**Problem.** Existing sibling projects cover generic research (atlas-research), coding (orion-code), and eval (vertex-eval), but none is specialized to *autonomously* research **AI, AI Agents, Agentic AI, and Harness Engineering** literature. The domain has specific requirements: heavy arxiv preprint flow, fast-moving taxonomy, claim-vs-cited-source verification, and the need to detect when a technique is *new* vs. *rebranded*.

**Why now.** The corpus in [../../docs/](../../docs/) (68 files) converges on a consensus harness architecture; SemaClaw (arXiv 2604.11548 / `midea-ai/SemaClaw`) contributes DAG Teams + PermissionBridge + SOUL.md + agentic wiki as general-purpose primitives; [../../docs/67-recommended-breakthrough-project.md](../../docs/67-recommended-breakthrough-project.md) names Gnomon's primitive-level failure attribution as the field's open problem. OpenFang fills the gap by applying SemaClaw's structural discipline + Gnomon's attribution to the narrow domain of **AI/agent research**.

**Outcome.** A deterministic-scheduler, DAG-planned, claim-verified research agent where every output ships with (a) evidence-bound citations, (b) cross-channel verification, (c) a growing literature knowledge-base + citation graph, and (d) a reusable research-skill library. Built TDD-first so every primitive has a rubric *before* an implementation.

---

## 2. Goals and Non-Goals

### Goals
1. Autonomously produce faithful, citation-bound research briefings on AI / Agentic AI / Harness Engineering topics.
2. Maintain a versioned literature KB + citation graph that compounds value across sessions.
3. Enforce claim-evidence binding — no prose-only citations.
4. Measure with Claw-Eval-shape rubrics (Pass@k *and* Pass^k, three evidence channels).
5. Be TDD-first: every DAG primitive has a test before implementation.

### Non-Goals (explicit scope cuts)
- **No multi-channel adapters** (Telegram/Feishu/QQ) — drop SemaClaw's `src/channels/`.
- **No web UI in v1** — defer graph-viewer to v2.
- **No paid-corpus connectors** in v1 — arxiv + Semantic Scholar + GitHub only.
- **No self-modifying scaffold code** in v1 — skill library only (Hermes pattern), defer full Autogenesis.
- **No agent-chaos-engineering layer** in v1 — Gnomon-style fault injection is v2.

---

## 3. Architecture Overview

### 3.1 The OpenFang Loop (DAG Teams adapted for research)

Two-phase, SemaClaw-shaped ([../../docs/54-semaclaw-general-purpose-agent.md](../../docs/54-semaclaw-general-purpose-agent.md)):

1. **Phase 1 — LLM Planner** emits a typed research DAG from the user brief + `FANG.md` persona + KB lookups.
2. **Phase 2 — Deterministic Scheduler** walks the DAG, parallelizes independent branches, parks permission-gated nodes without blocking siblings, retries at node granularity.

Canonical node types (research-specialized from SemaClaw's generic `search/reason/call-tool/hand-off`):

```
kb.lookup              search.arxiv            search.semantic_scholar
search.github          fetch.pdf               parse.latex
extract.claims         verify.claim            resolve.citation
summarize.section      compare.papers          synthesize.briefing
kb.promote             permission.request      reason                hand-off
```

### 3.2 The subagent roster (from [../../docs/02-subagent-delegation.md](../../docs/02-subagent-delegation.md))

| Subagent | Role | Inherits from |
|---|---|---|
| `SurveyAgent` | Breadth scan over a topic | atlas-research planner |
| `DeepReadAgent` | Full-paper read → structured extraction | new |
| `ClaimVerifierAgent` | Check a claim matches its cited source | orion-code verifier pattern |
| `SynthesisAgent` | Write briefing with structural claim bindings | atlas-research synthesizer |
| `CriticAgent` | Chain-of-verification / self-refine ([../../docs/18-chain-of-verification-self-refine.md](../../docs/18-chain-of-verification-self-refine.md)) | new |

### 3.3 Memory tiers (three-tier, SemaClaw-shaped)

- **Working memory** — per-DAG-run compressed state.
- **Retrieval memory** — agent's own session history, vector+FTS.
- **Persona partition `FANG.md`** — size-capped, never-compacted, version-controlled: user's domains of interest, evidence bar (peer-reviewed vs. preprint), citation style, known-read papers, venue preferences.

### 3.4 Literature KB + Citation Graph (OpenFang-specific)

Replaces SemaClaw's agentic personal-facts wiki. SQLite + FTS5 + pgvector-compatible embedding column. Entities: `Paper`, `Claim`, `Author`, `Venue`, `Technique`, `Benchmark`. Edges: `cites / extends / refutes / shares-author / same-benchmark / same-technique-family`. Promotion requires a citation anchor; nothing enters without it.

### 3.5 Verifier-evaluator loop ([../../docs/11-verifier-evaluator-loops.md](../../docs/11-verifier-evaluator-loops.md))

`SynthesisAgent` generates → `CriticAgent` critiques → `ClaimVerifierAgent` re-checks against original sources → gate. Separates generator from judge; judge never sees the generator's reasoning chain, only its artifact + the source.

### 3.6 Observability & attribution ([../../docs/67-recommended-breakthrough-project.md](../../docs/67-recommended-breakthrough-project.md))

Every DAG node emits a Gnomon-shaped primitive span (type, inputs, outputs, latency, cost, verdict, error). Failures attributed to the specific primitive that caused them. This is the telemetry floor; it enables the v2 skill-extraction loop.

---

## 4. File Architecture

Mirrors atlas-research's shape (the closest analogue), adapted for DAG-Teams orchestration:

```
open-fang/
├── README.md
├── plan.md                          ← this file
├── pyproject.toml                   # Python 3.11; FastAPI, pydantic 2, httpx, sqlite-fts5, numpy
├── Makefile                         # install | test | lint | run | docker-{up,down}
├── Containerfile                    # python:3.11-slim; vendors harness_core/
├── docker-compose.yml               # port 8010; healthcheck
├── .env.example                     # ANTHROPIC_API_KEY, ARXIV_EMAIL, S2_API_KEY
├── FANG.md                          # persona partition (checked-in seed + user-writable)
│
├── harness_core/                    # vendored from sibling projects (unchanged)
│   └── src/harness_core/            # models, messages, tools, permissions, hooks,
│                                    #   memory, observability, loop (see atlas-research)
│
├── docs/
│   ├── architecture.md              # big-picture; references this plan
│   ├── architecture-tradeoff.md     # rejected alternatives (see §6 below)
│   ├── system-design.md             # API, deployment, SLOs
│   └── blocks/
│       ├── 01-intake-brief.md
│       ├── 02-dag-planner.md        # LLM planner → typed DAG
│       ├── 03-scheduler.md          # deterministic walker + parking + retries
│       ├── 04-source-router.md      # arxiv / S2 / github dispatch
│       ├── 05-fetcher-parser.md     # PDF fetch, LaTeX parse
│       ├── 06-claim-extractor.md
│       ├── 07-citation-resolver.md  # build KB edges
│       ├── 08-claim-verifier.md     # claim ↔ source evidence span
│       ├── 09-synthesizer.md        # structural claim-evidence binding
│       ├── 10-critic-loop.md        # chain-of-verification
│       ├── 11-kb-and-graph.md       # SQLite+FTS5 schema, edge semantics
│       ├── 12-permission-bridge.md  # runtime-enforced risk gate
│       ├── 13-memory-tiers.md       # working / retrieval / FANG.md
│       ├── 14-observability.md      # Gnomon-shaped primitive spans
│       └── 15-skill-library.md      # (v2 slot) Hermes/Voyager shape
│
├── src/open_fang/
│   ├── __init__.py                  # public API: OpenFangPipeline, Brief, Report
│   ├── app.py                       # FastAPI: POST /v1/research, GET /v1/kb/*, /healthz
│   ├── models.py                    # Pydantic: Brief, DAG, Node, Claim, Evidence, Report
│   │
│   ├── planner/
│   │   ├── __init__.py
│   │   ├── llm_planner.py           # Phase-1 LLM DAG emission
│   │   ├── schema.py                # DAG schema validator + cycle/orphan checker
│   │   └── replanner.py             # on schema fail, one retry
│   │
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── engine.py                # Phase-2 deterministic walker
│   │   ├── parking.py               # permission-gated node parking
│   │   ├── retries.py               # exponential backoff, node-local
│   │   └── cost_router.py           # cheap vs. strong model selection per node
│   │
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── arxiv.py                 # ArxivSource (httpx + Atom parse)
│   │   ├── semantic_scholar.py      # S2Source
│   │   ├── github.py                # GithubSource (code-for-paper)
│   │   └── mock.py                  # MockSource for tests (canned fixtures)
│   │
│   ├── extract/
│   │   ├── __init__.py
│   │   ├── pdf_fetch.py             # arxiv PDF → bytes + caching
│   │   ├── latex_parse.py           # LaTeX → sections, equations, tables, refs
│   │   └── claims.py                # section → list[Claim] with evidence spans
│   │
│   ├── verify/
│   │   ├── __init__.py
│   │   ├── claim_verifier.py        # claim × source → verdict + span
│   │   ├── cross_channel.py         # abstract ∧ body ∧ table agree
│   │   └── critic.py                # CoV / self-refine loop
│   │
│   ├── synthesize/
│   │   ├── __init__.py
│   │   └── writer.py                # structural evidence_ids binding
│   │
│   ├── kb/
│   │   ├── __init__.py
│   │   ├── schema.sql               # Paper/Claim/Author/Venue/Technique/Benchmark
│   │   ├── store.py                 # SQLite + FTS5 + embeddings
│   │   ├── graph.py                 # edge semantics; citation-graph queries
│   │   └── promote.py               # citation-anchored promotion gate
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── working.py               # per-run compressed state
│   │   ├── retrieval.py             # session history vector+FTS
│   │   └── fang.py                  # FANG.md loader; never-compact guard
│   │
│   ├── permissions/
│   │   ├── __init__.py
│   │   ├── bridge.py                # runtime-enforced risk gate
│   │   └── tokens.py                # session / approve-once / pattern-bundled
│   │
│   ├── observe/
│   │   ├── __init__.py
│   │   ├── spans.py                 # Gnomon-shaped primitive spans
│   │   └── tracer.py                # JSON-to-stdout; trace_id correlation
│   │
│   └── pipeline.py                  # OpenFangPipeline.run(brief) orchestration
│
├── skills/                          # (v2) SKILL.md plugin dir, Claude Code shape
│   └── .gitkeep
│
├── tests/
│   ├── conftest.py                  # pytest fixtures: MockLLM, MockSource, tmp_kb
│   ├── fixtures/
│   │   ├── papers/                  # 6–10 curated arxiv PDFs + LaTeX + expected claims
│   │   ├── rubrics/                 # Claw-Eval-shape rubric JSON per paper
│   │   └── dags/                    # expected DAGs per brief
│   │
│   ├── unit/
│   │   ├── test_planner_schema.py
│   │   ├── test_scheduler_engine.py
│   │   ├── test_scheduler_parking.py
│   │   ├── test_sources_arxiv.py
│   │   ├── test_extract_claims.py
│   │   ├── test_verify_claim.py
│   │   ├── test_verify_cross_channel.py
│   │   ├── test_synthesize_binding.py
│   │   ├── test_kb_promote.py
│   │   ├── test_kb_graph_edges.py
│   │   ├── test_permissions_bridge.py
│   │   ├── test_memory_fang_no_compact.py
│   │   └── test_observe_spans.py
│   │
│   ├── integration/
│   │   ├── test_pipeline_happy_path.py    # brief → report end-to-end on fixtures
│   │   ├── test_pipeline_parking.py       # permission parked, siblings proceed
│   │   ├── test_pipeline_retry.py         # node fail → retry → success
│   │   └── test_pipeline_fabricated.py    # planted fake citation → verifier blocks
│   │
│   └── evaluation/
│       ├── test_passk.py                  # Pass@k across 20 briefs
│       ├── test_passk_repeated.py         # Pass^k rolling window
│       └── test_faithfulness_ratio.py     # verified_claims / total_claims ≥ 0.9
│
└── .github/workflows/ci.yml         # pytest + ruff + mypy; no paid-key CI
```

**Critical files to read when extending:** [../atlas-research/src/atlas_research/pipeline.py](../atlas-research/src/atlas_research/pipeline.py), [../atlas-research/src/atlas_research/verifier.py](../atlas-research/src/atlas_research/verifier.py), [../orion-code/src/orion_code/agent.py](../orion-code/src/orion_code/agent.py), [../vertex-eval/src/vertex_eval/passk.py](../vertex-eval/src/vertex_eval/passk.py), and the canonical [../../docs/54-semaclaw-general-purpose-agent.md](../../docs/54-semaclaw-general-purpose-agent.md).

---

## 5. Techniques Used — with Trade-offs

| Technique | Why | Trade-off | Chosen |
|---|---|---|---|
| **DAG Teams (ReWOO-shape) over ReAct** | Fault locality; parallel retrieval; deterministic scheduler [../../docs/17-rewoo.md](../../docs/17-rewoo.md), [../../docs/54-semaclaw-general-purpose-agent.md](../../docs/54-semaclaw-general-purpose-agent.md) | Less adaptive mid-run; needs replanner on cycles | ✅ |
| **Plan-Mode before act** [../../docs/03-plan-mode.md](../../docs/03-plan-mode.md) | Catches misunderstandings cheaply before cost | Small latency hit | ✅ |
| **Agentic RAG** [../../docs/25-agentic-rag.md](../../docs/25-agentic-rag.md) | Agent decides retrieve-vs-not, re-queries on fail | More tokens than fixed RAG | ✅ |
| **Three-tier memory + FANG.md** | Persona survives compaction; research preferences durable | Extra file management | ✅ |
| **Literature KB + citation graph (SQLite+FTS5)** | Compounds value across sessions; local-first, zero ops | No multi-tenant; not horizontally scalable | ✅ (v1) |
| **Verifier-evaluator loop (3-agent)** [../../docs/11-verifier-evaluator-loops.md](../../docs/11-verifier-evaluator-loops.md) | Independent judgment; blocks fabricated citations | 2× inference cost on verify path | ✅ |
| **Chain-of-Verification** [../../docs/18-chain-of-verification-self-refine.md](../../docs/18-chain-of-verification-self-refine.md) | Reduces hallucinated claims on synthesis | Extra round-trip per claim | ✅ |
| **Claw-Eval discipline (Pass@k + Pass^k)** [../../docs/38-claw-eval.md](../../docs/38-claw-eval.md) | Cross-channel evidence; reliability not just capability | Requires fixture curation | ✅ |
| **Gnomon-shape primitive spans** [../../docs/67-recommended-breakthrough-project.md](../../docs/67-recommended-breakthrough-project.md) | Attributes failures to primitives, not "the trace failed" | Upfront schema work | ✅ (telemetry v1; full HIR v2) |
| **MCP tool substrate** [../../docs/07-model-context-protocol.md](../../docs/07-model-context-protocol.md) | Portable across harnesses; matches SemaClaw repo | MCP stack adds dep surface | ✅ |
| **Hooks for pre/post tool** [../../docs/05-hooks.md](../../docs/05-hooks.md) | Deterministic validation; not prompt-shaped guardrails | Hook ordering bugs possible | ✅ |
| **PermissionBridge (runtime-enforced)** | Paid APIs / large downloads gated by code, not LLM | Some UX friction on approve | ✅ |
| **Tree of Thoughts / LATS** [../../docs/15-tree-of-thoughts-lats.md](../../docs/15-tree-of-thoughts-lats.md) | Look-ahead search for synthesis | 5–10× cost; rarely needed for research | ❌ v1 |
| **Reflexion episodic lessons** [../../docs/14-reflexion.md](../../docs/14-reflexion.md) | Learns across runs | Needs objective feedback signal | ⏸ v2 (skill library covers) |
| **Voyager skill library** [../../docs/19-voyager-skill-libraries.md](../../docs/19-voyager-skill-libraries.md) | Research-subroutines compound | Requires extractor + verifier | ⏸ v2 |
| **Agent chaos engineering** [../../docs/53-chaos-engineering-next-era.md](../../docs/53-chaos-engineering-next-era.md) | Fault injection → recovery tests | Adds test complexity | ⏸ v2 |
| **Full Autogenesis self-modification** [../../docs/36-autogenesis-self-evolving-agents.md](../../docs/36-autogenesis-self-evolving-agents.md) | Agent patches its own scaffold | Unsafe without a mesa-guard; v3+ | ❌ v1/v2 |

**Rejected alternatives** (captured for `architecture-tradeoff.md`):
- *Single-loop ReAct* — chosen against because long-horizon research tasks lose coherence; node-local retries are impossible.
- *Agent-chat multi-agent (AutoGen/CrewAI shape)* — chosen against because free-form chat is the orchestration-fragility mode SemaClaw explicitly fixes.
- *Neo4j for citation graph* — chosen against in v1 because SQLite+FTS5 meets needs at zero ops cost; revisit at >100k papers.
- *Full Gnomon HIR implementation* — chosen against in v1 because Gnomon itself is the sibling breakthrough project; OpenFang only *consumes* the span shape.

---

## 6. TDD Strategy

**Rule.** For every DAG primitive and every subagent, the **rubric item is written before the implementation**. Rubrics are Claw-Eval-shape JSON in `tests/fixtures/rubrics/`.

**Red-green-refactor per primitive.** Each node type in §3.1 gets one unit test file under `tests/unit/` plus a fixture in `tests/fixtures/`.

**Fixture discipline.**
- 6–10 curated arxiv papers (mix of AI-agent / harness-engineering / agentic AI) with:
  - Raw PDF
  - Parsed LaTeX (hand-corrected)
  - Expected claim list with evidence spans
  - Expected citation edges
  - Expected DAG for a canonical brief about the paper
- 20 canonical briefs for Pass@k / Pass^k eval.
- All LLM calls in tests use `MockLLM` with scripted outputs. No paid keys in CI.

**Test tiers.**
1. **Unit** — every module in `src/open_fang/*/`, ≥85% line coverage, ≤50ms per test.
2. **Integration** — full pipeline on fixtures, 4 scenarios (happy path, permission parking, retry, fabricated-citation block).
3. **Evaluation** — Pass@k, Pass^k rolling window, faithfulness ratio (verified_claims / total_claims). Rubric-gated: PR blocks if faithfulness < 0.90 on the 20-brief eval set.

**Dogfood.** Each release runs OpenFang itself on the five most recent arxiv AI/agent papers — outputs go to `docs/dogfood/<date>/` and are reviewed by the maintainer. Any failure becomes a fixture.

---

## 7. Implementation Phases

| Phase | Scope | Exit criteria |
|---|---|---|
| **0 — Scaffold** | Clone atlas-research layout; vendor harness_core; empty modules; CI green | `make test` passes with skeleton tests; healthz returns ok |
| **1 — Core DAG** | Planner (LLM → typed DAG), Scheduler (walk + retry), schema validator, MockSource, MockLLM | Integration test `test_pipeline_happy_path.py` green on MockSource |
| **2 — Real sources** | ArxivSource + S2Source + GithubSource; PDF fetch + caching; LaTeX parse | Dogfood run produces a briefing on 1 real paper with ≥3 verified claims |
| **3 — Verification** | ClaimVerifier + cross-channel + CriticAgent + synthesis binding | `test_pipeline_fabricated.py` green; faithfulness ≥ 0.90 on 5-paper set |
| **4 — KB + Graph** | SQLite schema, promotion gate, citation-graph edges, kb.lookup node | Second run on same topic uses KB; measurable redundant-fetch drop |
| **5 — Persona & Permissions** | FANG.md loader + never-compact; PermissionBridge + token kinds | Parking test green; persona survives 10-turn compaction test |
| **6 — Eval suite** | 20 briefs; Pass@k + Pass^k; faithfulness CI gate | Eval CI green; SLA floor set |
| **7 — Release v1** | Docs, Containerfile, docker-compose | `make docker-up` → POST /v1/research returns a real briefing |
| **v2 backlog** | Skill library (Hermes/Voyager); chaos engineering; web graph viewer; MCP server export | — |

---

## 8. API surface (v1)

```
POST /v1/research        Brief → Report (+ markdown + citations + verified_claims)
GET  /v1/kb/papers       list
GET  /v1/kb/paper/{id}   detail with citation edges
GET  /v1/kb/graph        citation subgraph by topic/author/technique
POST /v1/permissions/approve   token grant (session / once / pattern)
GET  /healthz            {"status":"ok","service":"open-fang"}
```

`Brief` fields: `question`, `domain` (default: infer from FANG.md), `max_cost_usd`, `min_papers`, `require_peer_reviewed`, `target_length_words`, `style`.

`Report` fields: `summary`, `sections[]` (each with `claims[]` where every `claim.evidence_ids[]` references `evidence[]`), `citations[]`, `techniques_extracted[]`, `cost_usd`, `faithfulness_ratio`, `verified_claims`, `total_claims`, `dag_id`, `trace_id`.

---

## 9. Verification Plan (end-to-end)

1. `make install && make test` — all unit + integration tests green; coverage ≥85%.
2. `make run` — `POST /v1/research` with `{"question": "What is ReWOO and how does it compare to ReAct for long-horizon tasks?"}` returns a briefing citing [../../docs/17-rewoo.md](../../docs/17-rewoo.md)-equivalent sources with faithfulness_ratio ≥ 0.90 and ≥3 citation-graph edges in the KB.
3. **Fabricated-citation probe.** Inject a fixture where a planted paper cites a non-existent reference; `test_pipeline_fabricated.py` confirms the verifier blocks synthesis.
4. **Permission parking probe.** Request a paywalled fetch; confirm the node parks, sibling nodes complete, and the briefing renders with an explicit gap note.
5. **Compaction resistance probe.** Run 10 turns; confirm `FANG.md` contents appear verbatim in the final turn's context.
6. **Dogfood.** Run OpenFang on the 5 most recent arxiv submissions in cs.AI agent-related categories; maintainer reviews each briefing; any hallucination or missed verification becomes a new fixture.
7. **Pass^k floor.** On the 20-brief eval set, k=5 repeats, Pass^5 ≥ 0.70 gates a release tag.

---

## 10. Open Questions (resolve before execution)

- **Embedding model** — local (bge-small, sentence-transformers) vs. hosted. Default: local for v1 to keep CI hermetic.
- **Pricing ceiling per brief** — enforced by `cost_router`; default suggestion `$0.50` for v1, revisit after dogfood.
- **FANG.md seed contents** — propose a minimal seed (AI/agent domains, evidence bar "arxiv OK", citation style "APA-inline + arxiv id"). Final wording is the user's.
- **License** — inherit MIT from SemaClaw or match sibling projects. Default: MIT.
