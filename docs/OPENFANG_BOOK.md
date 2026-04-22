# The OpenFang Book

> An autonomous AI research agent for AI / Agentic AI / Harness Engineering literature. Built TDD-first across v1 through v8.7, 612 tests, 25+ subsystems. This document explains the project from basic ideas to deep architecture to open research, in one file, navigable top-to-bottom or by direct TOC jump.

---

## Table of contents

- [Part 0 — Orientation](#part-0--orientation)
- [Part 1 — The problem OpenFang exists to solve](#part-1--the-problem-openfang-exists-to-solve)
- [Part 2 — The core ideas, basic to deep](#part-2--the-core-ideas-basic-to-deep)
- [Part 3 — The pipeline, end to end](#part-3--the-pipeline-end-to-end)
- [Part 4 — Subsystems tour](#part-4--subsystems-tour)
- [Part 5 — Techniques catalog](#part-5--techniques-catalog)
- [Part 6 — Evolution narrative (v1 → v8)](#part-6--evolution-narrative-v1--v8)
- [Part 7 — Ecosystem integration map](#part-7--ecosystem-integration-map)
- [Part 8 — What's genuinely novel](#part-8--whats-genuinely-novel)
- [Part 9 — Further improvements + open research](#part-9--further-improvements--open-research)
- [Part 10 — How to read the code + glossary](#part-10--how-to-read-the-code--glossary)
- [Appendix A — Source file index](#appendix-a--source-file-index)
- [Appendix B — Test catalog](#appendix-b--test-catalog)
- [Appendix C — Planning document lineage](#appendix-c--planning-document-lineage)

---

## Part 0 — Orientation

### One-sentence pitch

**OpenFang** is an autonomous AI research agent specialized for AI, AI Agents, Agentic AI, and Harness Engineering literature. It takes a research brief, plans a DAG of retrieval and verification steps, executes them deterministically, synthesizes an evidence-bound briefing, and grades its own output across seven quality signals — all while keeping every claim structurally tied to its source.

### The four-corner theme

Across eight major releases, OpenFang's capabilities cluster under four verbs:

| Version | Theme | Closes the loop on |
| --- | --- | --- |
| **v5** | **Speaks** | agentskills.io / claude-mem / Hermes / multica — every major agent-ecosystem contract |
| **v6** | **Debugs** | primitive-level failure attribution via HAFC-lite (12 primitives, rules-first) |
| **v7** | **Scales** | bounded token cost — sandbox + hybrid search + halt + delta + compression |
| **v8** | **Wires** | self-populating knowledge graph at zero LLM cost (GBrain pattern) |

v1–v4 built the foundations on which v5–v8 specialized.

### How to read this document

Three paths depending on why you're here:

- **New engineer joining the project** — read Parts 0 → 1 → 2 → 3 → 10. ~30 min. You'll know what exists and where to look.
- **Architect evaluating adoption** — read Parts 0 → 4 → 5 → 7 → 8. ~30 min. You'll know what's in the box and what's novel.
- **Existing maintainer** — skim Parts 6 → 9, jump to Appendices. ~15 min. You'll see what still needs deciding.

Every capability claim in this document links to the test that proves it. Every technique links to its source file. No number is stated without a citation.

---

## Part 1 — The problem OpenFang exists to solve

### What goes wrong without OpenFang

Ask a vanilla LLM to "research ReWOO and how it compares to ReAct" and you'll observe six failure modes, compounding in a long session:

1. **Fabricated citations.** The LLM invents plausible-sounding arxiv IDs that don't exist.
2. **Unbound claims.** The LLM asserts "ReWOO reduces tokens 5×" with no evidence span.
3. **No memory.** A second session asking the same question repeats every retrieval.
4. **Verbose responses.** The briefing is 3× longer than it needs to be, padded with filler.
5. **No failure attribution.** When the output is wrong, you can't tell *which step* broke.
6. **Token cost drift.** Every session consumes more tokens than the last because context bloat is invisible.

These are the six specific problems OpenFang was built to fix. Each has a named subsystem with tests that prove the fix works.

### Mapping problems to subsystems

| Problem | OpenFang subsystem | Verified by |
| --- | --- | --- |
| Fabricated citations | 5-tier verifier + security probes | [tests/integration/test_pipeline_fabricated.py](../tests/integration/test_pipeline_fabricated.py), [tests/evaluation/test_security_corpus.py](../tests/evaluation/test_security_corpus.py) |
| Unbound claims | Synthesis writer + lexical tier | [tests/unit/test_synthesize_binding.py](../tests/unit/test_synthesize_binding.py) |
| No memory | KB + progressive-disclosure memory | [tests/integration/test_kb_two_runs.py](../tests/integration/test_kb_two_runs.py), [tests/evaluation/test_progressive_token_reduction.py](../tests/evaluation/test_progressive_token_reduction.py) |
| Verbose responses | Caveman-style compression | [tests/unit/test_v7_6.py](../tests/unit/test_v7_6.py) |
| No failure attribution | HAFC-lite (12 primitives) | [tests/unit/test_attribution.py](../tests/unit/test_attribution.py) |
| Token cost drift | Sandbox + degradation monitor | [tests/integration/test_sandbox_pipeline.py](../tests/integration/test_sandbox_pipeline.py), [tests/unit/test_degradation_monitor.py](../tests/unit/test_degradation_monitor.py) |

### Why a narrow domain matters

OpenFang is not a general research agent. It's a research agent **for research-agent research** — a narrow domain that is itself recursive. This is unique among agents we've surveyed: no other tool (claude-mem, multica, Hermes Agent, gstack, ECC, GBrain) can research its own literature.

That recursion unlocks one of OpenFang's genuinely novel features: the **self-research loop** ([src/open_fang/self_research.py](../src/open_fang/self_research.py)) extracts Open Questions from each version-plan file and runs the pipeline on them. v8's [v8-plan.md](../v8-plan.md) was informed by v7's self-research output.

---

## Part 2 — The core ideas, basic to deep

Three concentric layers. Finish one before descending to the next.

### Layer 1 — Basic (what an agent loop is)

**Agent loop.** A program that, given a goal, decides what to do next by interleaving (a) a reasoning step, (b) a tool call, (c) an observation, (d) another reasoning step. Canonical shape: `ReAct` (Reasoning + Acting, Yao et al. 2022).

**Research agent.** An agent whose tools are retrieval (arxiv/S2/GitHub/HuggingFace) + reading + synthesis. Output is a briefing or a verified claim list.

**Evidence-bound claim.** A statement plus one or more `evidence_ids` pointing to source snippets. OpenFang refuses to emit a claim without an `evidence_ids` array. See [src/open_fang/models.py](../src/open_fang/models.py).

**DAG-teams orchestration (SemaClaw pattern).** Instead of a free-form ReAct loop, OpenFang's planner emits a **typed Directed Acyclic Graph** of steps; a deterministic scheduler walks it. Fault locality at the node: if one node fails, the rest keep running. See [src/open_fang/planner/llm_planner.py](../src/open_fang/planner/llm_planner.py) and [src/open_fang/scheduler/engine.py](../src/open_fang/scheduler/engine.py).

### Layer 2 — Intermediate (why OpenFang is different)

**Verifier-evaluator loop.** Every claim passes through 5+ independent tiers before it reaches the report. Lexical overlap → mutation-robust → LLM judge → executable → symbolic. Later tiers are skipped when an earlier one rejects (lexical short-circuit). See [src/open_fang/verify/claim_verifier.py](../src/open_fang/verify/claim_verifier.py) and Part 4.

**Progressive-disclosure memory.** Memory is *three tiers by read cost*, not one tier by write order:
- **Tier A** — always-in-context compact index (~50-100 tokens per observation line).
- **Tier B** — paginated timeline, fetched on demand.
- **Tier C** — full JSON span, fetched per-id.

v3.1 shipped this with ≥5× token reduction vs raw transcript on a 10-turn fixture. See [src/open_fang/memory/store.py](../src/open_fang/memory/store.py) and [src/open_fang/memory/progressive.py](../src/open_fang/memory/progressive.py).

**Skill as a first-class artifact.** Each skill is a folder with a `SKILL.md` ([agentskills.io](https://agentskills.io) compatible). The registry navigates them — flat in v2, hierarchical in v5.1 (Corpus2Skill pattern). See [src/open_fang/skills/](../src/open_fang/skills/).

**Specialist cohort.** A 9-role team (Survey, DeepRead, ClaimVerifier, Methodologist, Synthesis, Critic, ThreatModeler, Publisher, ResearchDirector) where each role declares which node kinds it handles, which skills it owns, which verifier tiers it runs. See [src/open_fang/supervisor/specialist.py](../src/open_fang/supervisor/specialist.py).

### Layer 3 — Deep (what's genuinely novel)

**Primitive-level failure attribution (HAFC-lite).** When a pipeline run fails, 12 canonical primitives compete for the blame via rules-first classification: which of `planner`, `scheduler-dispatch`, `source-router`, `kb-lookup`, `synthesis`, `mutation-probe`, `llm-judge`, `executable-verifier`, `critic`, `memory-compact`, `skill-activation`, `permission-gate` is responsible? See [src/open_fang/attribution/classifier.py](../src/open_fang/attribution/classifier.py).

**Self-wiring knowledge graph (GBrain pattern).** Every paper upserted to the KB gets scanned with deterministic regex patterns (`arxiv-id`, `(Author, Year)`, technique names, benchmark names). Typed edges are created without any LLM calls. A reconciler preserves manually-inserted edges while expiring stale self-wired ones. See [src/open_fang/kb/self_wire.py](../src/open_fang/kb/self_wire.py), [src/open_fang/kb/cascades.py](../src/open_fang/kb/cascades.py), [src/open_fang/kb/reconciler.py](../src/open_fang/kb/reconciler.py).

**Bayesian observation validity.** Each memory observation carries an `(α, β)` beta-binomial state. Corroboration increments `α`; contradiction increments `β`. Old observations with high validity outrank newer ones with low validity. See [src/open_fang/memory/validity.py](../src/open_fang/memory/validity.py).

**Hybrid search with RRF.** FTS5 BM25 + dense-embedding cosine + optional local reranker, fused with Reciprocal Rank Fusion (k=60, QMD default). Backwards-compatible: absent embedder means BM25-only. See [src/open_fang/kb/hybrid_search.py](../src/open_fang/kb/hybrid_search.py).

**Merkle-tree incremental reindex.** Paper content splits into sentence chunks; each hashes to a leaf; the tree root fingerprints the paper. On re-upsert, only chunks whose hash changed get reindexed. See [src/open_fang/kb/merkle.py](../src/open_fang/kb/merkle.py).

**7-signal degradation monitor.** Faithfulness trend, retry rate, mutation-warning rate, critic-downgrade rate, attribution entropy, duplicate-fetch rate, verdict-flip rate. Each gets a grade S / A / B / C / D / F. Aggregate grade = worst signal. When ≥3 drop below C, the pipeline self-checkpoints. See [src/open_fang/observe/degradation.py](../src/open_fang/observe/degradation.py).

---

## Part 3 — The pipeline, end to end

One annotated trace of `OpenFangPipeline.run(Brief("What is ReWOO?"))`:

```
                   Brief + FANG.md + SkillRegistry
                              │
                              ▼
    ┌───────────────────────────────────────────────────────┐
    │ Phase 1 — DAGPlanner                                  │
    │   LLM emits typed DAG OR canonical fallback           │
    │   src/open_fang/planner/llm_planner.py                │
    │                                                       │
    │   Input:  Brief + persona                             │
    │   Output: DAG with typed nodes:                       │
    │           kb.lookup → search.arxiv → extract.claims   │
    │           → verify.claim → synthesize.briefing        │
    └───────────────────────────────────────────────────────┘
                              │  typed DAG
                              ▼
    ┌───────────────────────────────────────────────────────┐
    │ Phase 2 — SchedulerEngine                             │
    │   src/open_fang/scheduler/engine.py                   │
    │                                                       │
    │   Per node:                                           │
    │     1. Loop detector: seen this (kind, args) before?  │
    │     2. Parking: explicitly parked?                    │
    │     3. PermissionBridge: risk-gated?                  │
    │     4. Chaos: inject fault per env config?            │
    │     5. Supervisor: specialist claims this kind?       │
    │     6. Sandbox: if search.* returns >5KB, defer it    │
    │     7. Retry policy: node-local backoff               │
    │                                                       │
    │   Output: evidence[], parked[], failed[]              │
    └───────────────────────────────────────────────────────┘
                              │  evidence[]
                              ▼
    ┌───────────────────────────────────────────────────────┐
    │ SynthesisWriter                                       │
    │   src/open_fang/synthesize/writer.py                  │
    │   Every claim carries evidence_ids[] — no prose cites │
    └───────────────────────────────────────────────────────┘
                              │  Report with bound claims
                              ▼
    ┌───────────────────────────────────────────────────────┐
    │ ClaimVerifier — 5 tiers (+ Tier 4.5 symbolic)         │
    │   src/open_fang/verify/claim_verifier.py              │
    │                                                       │
    │   Tier 1  lexical overlap          free, always on    │
    │   Tier 2  mutation probe           warn-only          │
    │   Tier 3  LLM judge                JSON verdict       │
    │   Tier 4  executable (Vcode)       sandboxed exec     │
    │   Tier 4.5 symbolic claim-number   numeric assertion  │
    │   Tier 5  cross-channel flag       metadata only      │
    │                                                       │
    │   Plus (optional):                                    │
    │     • CriticAgent — chain-of-verification             │
    │     • CrossModelVerifier — 3-mode (review/adv/consult)│
    │     • RedTeamAgent — attempts to flip verification    │
    └───────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌───────────────────────────────────────────────────────┐
    │ AttributionClassifier (HAFC-lite)                     │
    │   src/open_fang/attribution/classifier.py             │
    │   Only runs when faithfulness < 0.9 or failed_nodes   │
    │   Emits (primitive, confidence, evidence_span) tuples │
    └───────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌───────────────────────────────────────────────────────┐
    │ DegradationMonitor (v7.2)                             │
    │   7 signals, S-F grades, checkpoint trigger           │
    │   src/open_fang/observe/degradation.py                │
    └───────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌───────────────────────────────────────────────────────┐
    │ KB promotion + self-wire + cascade + reconcile        │
    │   src/open_fang/kb/{promote,self_wire,cascades,       │
    │                     reconciler,backlink}.py           │
    │                                                       │
    │   • promote: verified claims → papers table           │
    │   • self-wire: regex citation extraction (zero LLM)   │
    │   • cascade: depth-1 inference rules                  │
    │   • reconcile: stale self-wire edges expired          │
    │   • backlink: index updated for ranking boost         │
    └───────────────────────────────────────────────────────┘
                              │
                              ▼
                      PipelineResult
          (report, attribution, degradation_grade,
           activated_skills, promotion, observation_ids,
           parked_nodes, failed_nodes, downgraded_claims)
```

Every stage is individually tested. Integration-level test in [tests/integration/test_pipeline_happy_path.py](../tests/integration/test_pipeline_happy_path.py) exercises the whole trace; [tests/integration/test_pipeline_fabricated.py](../tests/integration/test_pipeline_fabricated.py) exercises the rejection path.

### Failure semantics

The pipeline does not raise on partial failure. Instead:

- Failed nodes are captured in `result.failed_nodes[]`.
- Parked nodes (permission-gated) land in `result.parked_nodes[]`.
- Critic-downgraded claims land in `result.downgraded_claims[]`.
- Attribution identifies which primitive caused which failure.
- The report is still produced, with `faithfulness_ratio < 1.0`.

This is the **fault-locality** guarantee. A single bad source doesn't void an entire brief.

---

## Part 4 — Subsystems tour

Twelve load-bearing subsystems. Each gets: responsibility, source files, key abstractions, failure modes, tests of record.

### 4.1 planner/ — Phase-1 DAG planning

- **Responsibility.** Convert a `Brief` into a typed DAG of execution nodes.
- **Source.** [src/open_fang/planner/llm_planner.py](../src/open_fang/planner/llm_planner.py), [schema.py](../src/open_fang/planner/schema.py), [replanner.py](../src/open_fang/planner/replanner.py).
- **Key abstractions.** `DAGPlanner.plan(brief) → DAG`. Accepts optional `LLMProvider`; falls back to canonical 6-node DAG on JSON parse failure.
- **Failure modes.** Malformed JSON from LLM → caught, canonical DAG substituted. Missing dependency in DAG → `DAGSchemaError`. Cycle → rejected.
- **Tests.** [test_planner_llm.py](../tests/unit/test_planner_llm.py), [test_planner_schema.py](../tests/unit/test_planner_schema.py).

### 4.2 scheduler/ — Phase-2 deterministic walker

- **Responsibility.** Walk the DAG, dispatch nodes, handle retries, parking, chaos, loop detection, sandbox, and supervisor routing.
- **Source.** [src/open_fang/scheduler/engine.py](../src/open_fang/scheduler/engine.py), [parking.py](../src/open_fang/scheduler/parking.py), [retries.py](../src/open_fang/scheduler/retries.py), [chaos.py](../src/open_fang/scheduler/chaos.py), [loop_detector.py](../src/open_fang/scheduler/loop_detector.py).
- **Key abstractions.** `SchedulerEngine.run(dag) → (evidence, parked, failed)`. `ParkingRegistry`, `RetryPolicy`, `ChaosInjector`, `LoopDetector`.
- **Failure modes.** Node execution raises → retry (up to `max_attempts`) → mark failed. Chaos injection → `RuntimeError("chaos: network_drop...")`. Loop detected → cached output returned.
- **Tests.** [test_scheduler_engine.py](../tests/unit/test_scheduler_engine.py), [test_scheduler_parking.py](../tests/unit/test_scheduler_parking.py), [test_scheduler_permissions.py](../tests/unit/test_scheduler_permissions.py), [test_chaos_hooks.py](../tests/unit/test_chaos_hooks.py).

### 4.3 sources/ — External retrieval adapters

- **Responsibility.** Fetch evidence from arxiv / Semantic Scholar / GitHub / HuggingFace / MCP servers.
- **Source.** [arxiv.py](../src/open_fang/sources/arxiv.py), [arxiv_native.py](../src/open_fang/sources/arxiv_native.py), [semantic_scholar.py](../src/open_fang/sources/semantic_scholar.py), [github.py](../src/open_fang/sources/github.py), [github_native.py](../src/open_fang/sources/github_native.py), [huggingface.py](../src/open_fang/sources/huggingface.py), [mcp.py](../src/open_fang/sources/mcp.py), [mock.py](../src/open_fang/sources/mock.py), [router.py](../src/open_fang/sources/router.py).
- **Key abstractions.** `SourceRouter.search(kind, query)` dispatches to the right adapter. `MCPSpecSource` imports MCP manifests as KB entries. `ArxivNativeSource.fetch_references()` uses BibTeX.
- **Failure modes.** Network 4xx/5xx → caught, empty list returned. Malformed payload → adapter returns empty. Sandbox gate defers >5KB responses.
- **Tests.** [test_sources_arxiv.py](../tests/unit/test_sources_arxiv.py), [test_sources_s2.py](../tests/unit/test_sources_s2.py), [test_sources_github.py](../tests/unit/test_sources_github.py), [test_source_router.py](../tests/unit/test_source_router.py), [test_mcp_spec_source.py](../tests/unit/test_mcp_spec_source.py).

### 4.4 verify/ — Multi-tier claim verification

- **Responsibility.** Gate every claim through 5+ independent tiers before the report ships.
- **Source.** [claim_verifier.py](../src/open_fang/verify/claim_verifier.py), [llm_judge.py](../src/open_fang/verify/llm_judge.py), [mutation.py](../src/open_fang/verify/mutation.py), [executable.py](../src/open_fang/verify/executable.py), [symbolic.py](../src/open_fang/verify/symbolic.py), [critic.py](../src/open_fang/verify/critic.py), [redteam.py](../src/open_fang/verify/redteam.py), [cross_model.py](../src/open_fang/verify/cross_model.py), [router.py](../src/open_fang/verify/router.py), [halt.py](../src/open_fang/verify/halt.py).
- **Key abstractions.** `ClaimVerifier.verify(report, evidence)`; each tier runs conditionally on claim kind (v4.1 router). `ConfidenceMonitor` emits halt signal after 3 high-confidence verdicts (v6.1).
- **Failure modes.** Any tier rejection → `claim.verified = False` + `verification_note`. Tier 2 warns but doesn't veto. Tier 4 executable timeout → claim rejected with error.
- **Tests.** [test_verify_claim.py](../tests/unit/test_verify_claim.py), [test_verifier_tiers_2_and_4.py](../tests/unit/test_verifier_tiers_2_and_4.py), [test_symbolic_verifier.py](../tests/unit/test_symbolic_verifier.py), [test_cross_model_verifier.py](../tests/unit/test_cross_model_verifier.py), [test_claim_kind_router.py](../tests/unit/test_claim_kind_router.py).

### 4.5 synthesize/ — Evidence-bound briefing writer

- **Responsibility.** Compose a `Report` where every claim carries `evidence_ids[]`.
- **Source.** [writer.py](../src/open_fang/synthesize/writer.py), [compression.py](../src/open_fang/synthesize/compression.py).
- **Key abstractions.** `SynthesisWriter.write(brief, evidence) → Report`. `compress_report(report, mode="terse"|"ultra")` (v7.6).
- **Failure modes.** Empty evidence list → empty findings section (legal). Claim without evidence → lexical verifier rejects.
- **Tests.** [test_synthesize_binding.py](../tests/unit/test_synthesize_binding.py), [test_v7_6.py](../tests/unit/test_v7_6.py).

### 4.6 kb/ — SQLite+FTS5 knowledge base + citation graph

- **Responsibility.** Store papers, claims, edges; serve BM25 search; hybrid search with embeddings; self-wire citation edges on upsert; cascade + reconcile.
- **Source.** [store.py](../src/open_fang/kb/store.py), [promote.py](../src/open_fang/kb/promote.py), [graph.py](../src/open_fang/kb/graph.py), [edges.py](../src/open_fang/kb/edges.py), [random_walk.py](../src/open_fang/kb/random_walk.py), [embedders.py](../src/open_fang/kb/embedders.py), [hybrid_search.py](../src/open_fang/kb/hybrid_search.py), [merkle.py](../src/open_fang/kb/merkle.py), [self_wire.py](../src/open_fang/kb/self_wire.py), [cascades.py](../src/open_fang/kb/cascades.py), [entities.py](../src/open_fang/kb/entities.py), [reconciler.py](../src/open_fang/kb/reconciler.py), [backlink.py](../src/open_fang/kb/backlink.py), [decontamination.py](../src/open_fang/kb/decontamination.py), [schema.sql](../src/open_fang/kb/schema.sql).
- **Key abstractions.** `KBStore.upsert_paper()` / `search()` / `add_edge()`. `HybridSearch(kb, embedder, reranker)`. `SelfWirer(kb).process(paper_id, content)`. `CascadeEngine(kb).run_all()`. `reconcile_self_wired_edges()`.
- **Failure modes.** Apostrophes in queries — handled by `_to_fts_query` quoting. Missing embeddings — hybrid search degrades to BM25. Reconciler touching manual edges — **forbidden invariant**, filter by `provenance LIKE 'self-wire:%'`.
- **Tests.** [test_kb_store.py](../tests/unit/test_kb_store.py), [test_kb_promote_report.py](../tests/unit/test_kb_promote_report.py), [test_kb_graph_build.py](../tests/unit/test_kb_graph_build.py), [test_kb_edges.py](../tests/unit/test_kb_edges.py), [test_random_walk.py](../tests/unit/test_random_walk.py), [test_hybrid_search.py](../tests/unit/test_hybrid_search.py), [test_merkle.py](../tests/unit/test_merkle.py), [test_self_wire.py](../tests/unit/test_self_wire.py), [test_cascades.py](../tests/unit/test_cascades.py), [test_entities.py](../tests/unit/test_entities.py), [test_reconciler.py](../tests/unit/test_reconciler.py), [test_backlink.py](../tests/unit/test_backlink.py), [test_decontamination.py](../tests/unit/test_decontamination.py).

### 4.7 memory/ — Three-tier progressive-disclosure memory

- **Responsibility.** Persist pipeline observations across sessions with bounded context cost.
- **Source.** [fang.py](../src/open_fang/memory/fang.py), [working.py](../src/open_fang/memory/working.py), [store.py](../src/open_fang/memory/store.py), [progressive.py](../src/open_fang/memory/progressive.py), [context.py](../src/open_fang/memory/context.py), [validity.py](../src/open_fang/memory/validity.py), [sandbox.py](../src/open_fang/memory/sandbox.py), [retrieval.py](../src/open_fang/memory/retrieval.py).
- **Key abstractions.** `FANGLoader` (persona, never compacted). `WorkingBuffer` (rolling in-memory). `MemoryStore` (3-tier SQLite-backed). `ProgressiveContextAssembler` (persona + Tier A + last-N turns). `ToolOutputSandbox` (deferred payloads).
- **Failure modes.** FANG.md oversize → `ValueError`. Progressive tier fetch with missing ID → `None`. Sandbox handle unknown → empty list.
- **Tests.** [test_memory_fang_no_compact.py](../tests/unit/test_memory_fang_no_compact.py), [test_memory_store.py](../tests/unit/test_memory_store.py), [test_progressive_assembler.py](../tests/unit/test_progressive_assembler.py), [test_tool_output_sandbox.py](../tests/unit/test_tool_output_sandbox.py), [test_validity.py](../tests/unit/test_validity.py), [test_progressive_token_reduction.py](../tests/evaluation/test_progressive_token_reduction.py).

### 4.8 permissions/ — Runtime-enforced risk gates

- **Responsibility.** Mediate tool access based on node risk + user approval tokens.
- **Source.** [bridge.py](../src/open_fang/permissions/bridge.py), [tokens.py](../src/open_fang/permissions/tokens.py).
- **Key abstractions.** `PermissionBridge.check(op, risk) → "allow" | "park" | "deny"`. Token kinds: `session`, `once`, `pattern`.
- **Failure modes.** Medium risk without token → node parked (not failed). High risk without token → node failed. Approve endpoint consumes `once` tokens atomically.
- **Tests.** [test_permissions_bridge.py](../tests/unit/test_permissions_bridge.py), [test_api_permissions.py](../tests/integration/test_api_permissions.py).

### 4.9 observe/ — Gnomon-shape spans + degradation monitor

- **Responsibility.** Emit trace spans for every node; grade run quality across 7 signals.
- **Source.** [tracer.py](../src/open_fang/observe/tracer.py), [spans.py](../src/open_fang/observe/spans.py), [degradation.py](../src/open_fang/observe/degradation.py).
- **Key abstractions.** `SpanRecorder` collects `Span` objects. `DegradationMonitor.evaluate(result) → DegradationReport` with S-F grades.
- **Failure modes.** Missing attribution → entropy defaults to 2.5 (maximally diverse). Zero total claims → rates return 0 (not NaN).
- **Tests.** [test_observe_spans.py](../tests/unit/test_observe_spans.py), [test_degradation_monitor.py](../tests/unit/test_degradation_monitor.py).

### 4.10 skills/ — agentskills.io-compliant skill library

- **Responsibility.** Load, validate, activate, extract, evolve skills.
- **Source.** [schema.py](../src/open_fang/skills/schema.py), [loader.py](../src/open_fang/skills/loader.py), [registry.py](../src/open_fang/skills/registry.py), [tree.py](../src/open_fang/skills/tree.py), [extractor.py](../src/open_fang/skills/extractor.py), [diagnostician.py](../src/open_fang/skills/diagnostician.py), [arena.py](../src/open_fang/skills/arena.py).
- **Key abstractions.** `Skill` + `SkillFrontmatter` dataclasses. `SkillLoader` (4-location resolution). `SkillRegistry.activate(query)`. `SkillTree` (hierarchical navigation). `TrajectoryExtractor.extract(results)` → learned skills. `EvolvingArena.round(briefs)` → diagnose + extract.
- **Failure modes.** Missing required field → `SkillParseError`. `learned` origin without `confidence` → rejected. Category depth > 3 → `SkillTreeError`.
- **Tests.** [test_skill_schema.py](../tests/unit/test_skill_schema.py), [test_skill_loader.py](../tests/unit/test_skill_loader.py), [test_skill_registry.py](../tests/unit/test_skill_registry.py), [test_skill_agentskills_compat.py](../tests/unit/test_skill_agentskills_compat.py), [test_skill_extractor.py](../tests/unit/test_skill_extractor.py), [test_diagnostician.py](../tests/unit/test_diagnostician.py), [test_arena_loop.py](../tests/integration/test_arena_loop.py), [test_skill_tree.py](../tests/unit/test_skill_tree.py).

### 4.11 supervisor/ — 9-specialist cohort

- **Responsibility.** Route DAG nodes through role-specialized agents with per-role budgets, skills, and verifier-tier choices.
- **Source.** [registry.py](../src/open_fang/supervisor/registry.py), [specialist.py](../src/open_fang/supervisor/specialist.py), [isolated.py](../src/open_fang/supervisor/isolated.py).
- **Key abstractions.** `Supervisor.dispatch(node, context) → SpecialistOutcome`. `default_supervisor()` wires 9 specialists. `IsolatedSupervisor` (opt-in subprocess mode, v4.3).
- **Failure modes.** Specialist raises → `SpecialistOutcome.error` set, siblings continue (crash isolation). Isolated mode timeout → `"isolated-subprocess timeout"`.
- **Tests.** [test_supervisor.py](../tests/unit/test_supervisor.py), [test_specialists.py](../tests/unit/test_specialists.py), [test_v4_cohort.py](../tests/unit/test_v4_cohort.py), [test_isolated_supervisor.py](../tests/unit/test_isolated_supervisor.py), [test_scheduler_supervisor.py](../tests/integration/test_scheduler_supervisor.py).

### 4.12 attribution/ + mcp_server/ + trace/ + adapters/ + eval/ + security/

- **attribution/.** HAFC-lite classifier, 12 primitives. [classifier.py](../src/open_fang/attribution/classifier.py).
- **mcp_server/.** stdio (v2.6) + HTTP+Bearer (v8.6) JSON-RPC server exposing 7 read-only tools. [server.py](../src/open_fang/mcp_server/server.py), [http.py](../src/open_fang/mcp_server/http.py).
- **trace/.** Atropos-compatible trajectory export. [export.py](../src/open_fang/trace/export.py).
- **adapters/.** Multica runtime adapter. [multica.py](../src/open_fang/adapters/multica.py).
- **eval/.** Pass@k / Pass^k (Claw-Eval), feed parser + cron, graph metrics (BrainBench-analog), multi-hop brief synthesis. [passk.py](../src/open_fang/eval/passk.py), [feed.py](../src/open_fang/eval/feed.py), [feed_cron.py](../src/open_fang/eval/feed_cron.py), [graph_metrics.py](../src/open_fang/eval/graph_metrics.py), [synthesize.py](../src/open_fang/eval/synthesize.py).
- **security/.** Attack probes + static detector. [probes.py](../src/open_fang/security/probes.py).
- **chaos_scanner.py.** Chaos × HAFC fragility matrix.
- **self_research.py.** Open-questions extractor; research-OpenFang-on-itself.

---

## Part 5 — Techniques catalog

Every technique OpenFang uses, with its source, the version it landed in, the trade-off it makes, and the test that verifies it.

| Technique | Source | Version | Trade-off | Test of record |
| --- | --- | --- | --- | --- |
| DAG-teams orchestration | SemaClaw (arxiv:2604.11548) | v1.1 | less adaptive mid-run | [test_planner_schema.py](../tests/unit/test_planner_schema.py) |
| Canonical DAG fallback | OpenFang | v1.1 | rigid plan shape when LLM unavailable | [test_planner_llm.py](../tests/unit/test_planner_llm.py) |
| Evidence-bound claims | plan.md §1 | v1.1 | no prose citations ever | [test_synthesize_binding.py](../tests/unit/test_synthesize_binding.py) |
| ArxivSource (Atom) | arxiv API | v1.2 | stdlib XML parse | [test_sources_arxiv.py](../tests/unit/test_sources_arxiv.py) |
| 5-paper faithfulness floor | plan.md §6 | v1.3 | hand-curated fixtures | [test_five_paper_faithfulness.py](../tests/evaluation/test_five_paper_faithfulness.py) |
| LLM-judge verifier (JSON) | CriticAgent lit | v1.3 | 2× inference on verify path | [test_verifier_with_llm_judge.py](../tests/unit/test_verifier_with_llm_judge.py) |
| Citation graph + promotion gate | plan.md §3.4 | v1.4 | schema complexity | [test_kb_two_runs.py](../tests/integration/test_kb_two_runs.py) |
| Permission bridge (risk-gated) | SemaClaw | v1.5 | UX friction on approve | [test_scheduler_permissions.py](../tests/unit/test_scheduler_permissions.py) |
| Pass@k + Pass^k metrics | Claw-Eval / HumanEval | v1.6 | no single-score summary | [test_eval_passk.py](../tests/unit/test_eval_passk.py) |
| 5 curated SKILL.md (ECC shape) | everything-claude-code | v2.0 | folder convention | [test_skill_loader.py](../tests/unit/test_skill_loader.py) |
| Trajectory extractor | ECC `/skill-create` | v2.1 | shallow signature clustering | [test_skill_extractor.py](../tests/unit/test_skill_extractor.py) |
| Evolving arena loop | Agent-World (arxiv:2604.18292) | v2.1 | no RL, prompt-only | [test_arena_loop.py](../tests/integration/test_arena_loop.py) |
| Weighted random walk synthesis | Agent-World graph-walk | v2.2 | walk seed sensitivity | [test_random_walk.py](../tests/unit/test_random_walk.py), [test_multi_hop_synthesis.py](../tests/integration/test_multi_hop_synthesis.py) |
| Cytoscape.js graph viewer | OpenFang | v2.3 | read-only | [test_api_kb_graph.py](../tests/integration/test_api_kb_graph.py) |
| Mutation-robust verifier | Atomic Skills (arxiv:2604.05013) | v2.4 | warns, doesn't veto | [test_mutation_probe.py](../tests/unit/test_mutation_probe.py) |
| Executable (`Vcode`) verifier | Agent-World | v2.4 | sandbox + timeout required | [test_executable_verifier.py](../tests/unit/test_executable_verifier.py) |
| Mutation resistance ≥ 85% | OpenFang floor | v2.4 | hand-authored corpus | [test_mutation_resistance.py](../tests/evaluation/test_mutation_resistance.py) |
| Security probes (4 attacks) | awesome-papers §Security | v2.5 | seed attack list | [test_security_probes.py](../tests/unit/test_security_probes.py) |
| Chaos hooks (env-configured) | plan.md §5 | v2.5 | opt-in; can thrash | [test_chaos_hooks.py](../tests/unit/test_chaos_hooks.py) |
| Red-team subagent | gstack `/codex` | v2.5 | extra LLM cost | [test_security_corpus.py](../tests/evaluation/test_security_corpus.py) |
| MCP stdio server (4 tools) | anthropic/mcp | v2.6 | JSON-RPC 2.0 surface | [test_mcp_server.py](../tests/unit/test_mcp_server.py) |
| MCP manifest import | Agent-World | v2.6 | thin adapter | [test_mcp_spec_source.py](../tests/unit/test_mcp_spec_source.py) |
| Decontamination scan | Atomic Skills App. C.1 | v2.7 | regex false-positives | [test_decontamination.py](../tests/unit/test_decontamination.py) |
| AGENTS.md universal entry | ECC | v2.7 | small polish | — |
| agentskills.io schema alignment | nousresearch/hermes-agent | v3.0 | dual top-level + metadata | [test_skill_agentskills_compat.py](../tests/unit/test_skill_agentskills_compat.py) |
| Progressive-disclosure memory | thedotmack/claude-mem (clean-room) | v3.1 | +one LLM-summary call per span | [test_progressive_assembler.py](../tests/unit/test_progressive_assembler.py), [test_progressive_token_reduction.py](../tests/evaluation/test_progressive_token_reduction.py) |
| Token reduction ≥ 5× | plan.md §W2 | v3.1 | claim over naive baseline | [test_progressive_token_reduction.py](../tests/evaluation/test_progressive_token_reduction.py) |
| 5-specialist supervisor | v3-plan W3 | v3.2 | asyncio only, not subprocess | [test_supervisor.py](../tests/unit/test_supervisor.py) |
| Trajectory export (Atropos) | Hermes Agent | v3.3 | schema drift risk | [test_trajectory_export.py](../tests/unit/test_trajectory_export.py) |
| 9-specialist cohort | gstack 22 roles | v4.0 | expansion discipline | [test_v4_cohort.py](../tests/unit/test_v4_cohort.py) |
| Claim-kind router | OpenFang | v4.1 | rule-based classifier | [test_claim_kind_router.py](../tests/unit/test_claim_kind_router.py) |
| Three-mode cross-model verify | gstack `/codex` | v4.2 | 2× cost on high-risk claims | [test_cross_model_verifier.py](../tests/unit/test_cross_model_verifier.py) |
| Isolated-subprocess supervisor | gstack Conductor | v4.3 | ~500ms startup per specialist | [test_isolated_supervisor.py](../tests/unit/test_isolated_supervisor.py) |
| Lifecycle stage labels | gstack sprint discipline | v4.4 | enum growth | inline `Span.stage` |
| claude-mem MCP tool-name parity | thedotmack/claude-mem | v5.0 | namespace collision risk | [test_mcp_server.py](../tests/unit/test_mcp_server.py) |
| Skill-tree hierarchy | Corpus2Skill (arxiv:2604.14572) | v5.1 | depth + leaf caps | [test_skill_tree.py](../tests/unit/test_skill_tree.py) |
| Feed cron (opt-in) | v2.7 parser + v5 velocity | v5.4 | runaway-import risk | [test_feed_cron.py](../tests/unit/test_feed_cron.py) |
| Multica runtime adapter | multica-ai/multica | v5.5 | protocol drift risk | [test_multica_adapter.py](../tests/unit/test_multica_adapter.py) |
| HAFC-lite (12 primitives) | docs/67 Gnomon | v6.0 | rules-first, not trained | [test_attribution.py](../tests/unit/test_attribution.py) |
| ReBalance confidence halt | alexgreensh (clean-room) | v6.1 | opt-in, skips critic only | [test_confidence_halt.py](../tests/unit/test_confidence_halt.py) |
| Tier 4.5 symbolic verifier | docs/37 neuro-symbolic | v6.2 | ±15% tolerance | [test_symbolic_verifier.py](../tests/unit/test_symbolic_verifier.py) |
| Native arxiv BibTeX adapter | GBrain | v6.3 | best-effort parse | [test_arxiv_native.py](../tests/unit/test_arxiv_native.py) |
| Native GitHub PwC adapter | gstack | v6.3 | rate-limited API | [test_github_native.py](../tests/unit/test_github_native.py) |
| Native HuggingFace adapter | Agent-World | v6.3 | HF search heuristic | [test_huggingface_source.py](../tests/unit/test_huggingface_source.py) |
| Chaos × HAFC scanner | v2.5 + v6.0 | v6.4 | manual invocation | [test_chaos_scanner.py](../tests/unit/test_chaos_scanner.py) |
| Self-research loop | OpenFang unique | v6.5 | quarterly cadence | [test_self_research.py](../tests/unit/test_self_research.py) |
| Tool-output sandbox | Context Mode | v7.0 | threshold tuning | [test_tool_output_sandbox.py](../tests/unit/test_tool_output_sandbox.py) |
| Hybrid search (BM25+dense+RRF) | QMD + claude-context | v7.1 | embedding cost | [test_hybrid_search.py](../tests/unit/test_hybrid_search.py) |
| 7-signal degradation monitor | alexgreensh (clean-room) | v7.2 | threshold calibration | [test_degradation_monitor.py](../tests/unit/test_degradation_monitor.py) |
| Loop detector | alexgreensh (clean-room) | v7.2 | hash scope | [test_loop_detector.py](../tests/unit/test_loop_detector.py) |
| Bayesian validity | Token Savior | v7.3 | weak prior beta(2,2) | [test_validity.py](../tests/unit/test_validity.py) |
| Delta mode for re-reads | alexgreensh (clean-room) | v7.4 | content hash schema bump | [test_delta.py](../tests/unit/test_delta.py) |
| Merkle-tree incremental reindex | claude-context (Zilliz) | v7.5 | sentence-level only | [test_merkle.py](../tests/unit/test_merkle.py) |
| Caveman output compression | Caveman | v7.6 | 3 profiles | [test_v7_6.py](../tests/unit/test_v7_6.py) |
| Zero-LLM self-wiring | GBrain | v8.0 | regex false-positives | [test_self_wire.py](../tests/unit/test_self_wire.py) |
| Typed-edge cascades (depth-1) | GBrain inference cascade | v8.1 | edge explosion at scale | [test_cascades.py](../tests/unit/test_cascades.py) |
| Entity expansion (authors/affil/tech/bench) | GBrain + OpenFang-native | v8.2 | seeded-list maintenance | [test_entities.py](../tests/unit/test_entities.py) |
| Stale-link reconciler | GBrain reconciler | v8.3 | manual-edge preservation invariant | [test_reconciler.py](../tests/unit/test_reconciler.py) |
| Backlink-boosted ranking | GBrain | v8.4 | needs refreshable index | [test_backlink.py](../tests/unit/test_backlink.py) |
| BrainBench-analog eval | GBrain BrainBench | v8.5 | 20-paper fixture corpus | [test_graph_metrics.py](../tests/unit/test_graph_metrics.py) |
| Remote MCP + Bearer auth | GBrain remote-MCP | v8.6 | rate-limit bucket | [test_mcp_http.py](../tests/unit/test_mcp_http.py) |

60+ techniques. Every one has a test.

---

## Part 6 — Evolution narrative (v1 → v8)

Each OpenFang version opens with a pre-write `vN-plan.md` that names a theme, enumerates workstreams, commits to exit criteria. The plan ships before the code. **Plans are first-class artifacts** — part of how the project reasons about itself.

### v1 (1.0–1.7) — Scaffold + 5-tier floor

Built the testable spine: Pydantic models, DAG planner with canonical fallback, deterministic scheduler with retry/parking/permissions, 5-tier verifier (lexical → LLM-judge → cross-channel), SQLite+FTS5 KB with promotion gate, 20-brief eval corpus with Pass@k/Pass^k, Docker release. 129 tests at v1.7.

Key decision: **TDD-first, plan-first**. Every subsystem ships with rubrics in `tests/fixtures/rubrics/` before implementation.

### v2 (2.0–2.7) — Skills, KB graph, security, MCP

Added ECC-shaped skill library + trajectory extractor + evolving arena (v2.0–v2.1); edge extractor + multi-hop brief synthesis (v2.2); `/v1/kb/graph` cytoscape viewer (v2.3); Tier-2 mutation probe + Tier-4 executable verifier + 5-paper eval ≥ 0.90 faithfulness (v2.4); 4 security probes + chaos hooks + red-team (v2.5); stdio MCP server (v2.6); AGENTS.md + decontamination + 50-brief corpus (v2.7). 305 tests at v2.7.

Key pivot: v2.1 evolving arena introduces the concept of **diagnostician** (failure-trace reader) distinct from critic (single-claim verifier) — a pattern v6's HAFC later formalizes.

### v3 (3.0–3.3) — Interop + progressive memory + specialists

Aligned `SKILL.md` with agentskills.io (v3.0); progressive-disclosure memory with ≥5× token reduction (v3.1); supervisor + 5 specialists (v3.2); Atropos-compatible trajectory export (v3.3). 368 tests.

Key shift: v3 starts picking up patterns **from the ecosystem**, not just from papers. Hermes Agent's agentskills.io compliance, claude-mem's 3-tier memory, gstack-adjacent multi-specialist dispatch.

### v4 (4.0–4.4) — Cohort scaling + cross-model + stage labels

9-specialist cohort adds ResearchDirector, Methodologist, ThreatModeler, Publisher (v4.0); claim-kind router decides which tiers run per claim (v4.1); three-mode cross-model verification — review, adversarial, consultation (v4.2); IsolatedSupervisor with subprocess-per-specialist (v4.3); lifecycle stage labels on every span (v4.4). 402 tests.

Key insight: different claim kinds deserve different verifier budgets. Quantitative claims need mutation + executable; qualitative claims don't.

### v5 (5.0–5.6) — **Speaks** (ecosystem interop)

claude-mem MCP tool-name parity via `memory.search` / `memory.timeline` / `memory.get_observations` (v5.0); skill-tree hierarchy via Corpus2Skill pattern (v5.1); opt-in weekly feed cron pulling awesome-ai-agent-papers (v5.4); multica runtime adapter implementing task-assignment lifecycle (v5.5); release (v5.6). 425 tests.

**Four ecosystems now talk to OpenFang unchanged**: agentskills.io clients see a valid skill provider; claude-mem clients hit memory.* tools directly; Hermes Agent consumes our Atropos trajectories; multica teams can assign briefs to us as a runtime.

### v6 (6.0–6.6) — **Debugs** (failure attribution)

HAFC-lite with 12 primitives + rules-first classifier (v6.0); ReBalance-inspired confidence-steered halt (v6.1); Tier 4.5 symbolic claim-number verifier catching "claimed 10×, actual 5×" (v6.2); native arxiv BibTeX + GitHub PwC + HuggingFace adapters (v6.3); chaos × HAFC fragility scanner (v6.4); self-research loop that researches OpenFang's own plan files (v6.5); release (v6.6). 478 tests.

v6.5 is unique in the ecosystem — OpenFang researches its own research-agent literature.

### v7 (7.0–7.7) — **Scales** (bounded token cost)

Tool-output sandbox with FTS5-indexed deferral (v7.0); hybrid search (BM25 + dense + RRF + optional reranker) (v7.1); 7-signal degradation monitor + loop detector (v7.2); Bayesian memory validity (v7.3); delta-mode for source re-reads (v7.4); Merkle-tree incremental reindex (v7.5); Caveman-style output compression (v7.6); release (v7.7). 547 tests.

Key shift: v7 targets **token cost as a first-class metric**. Every mechanism in v7 cuts a category of waste that v1–v6 left unmitigated.

### v8 (8.0–8.7) — **Wires** (self-populating KB)

Zero-LLM self-wiring (regex citation extraction) on every upsert (v8.0); depth-1 cascade rules (v8.1); entity expansion for authors/affiliations/techniques/benchmarks (v8.2); stale-link reconciler preserving manual edges (v8.3); backlink-boosted search ranking (v8.4); BrainBench-analog graph metrics on our own 20-paper corpus (v8.5); remote MCP over HTTP with Bearer auth + rate limit (v8.6); release (v8.7). 612 tests.

GBrain thesis — "regex + pattern cascades on ingestion beats LLM orchestration on read" — proven inside OpenFang's domain. Graph density improves without added LLM cost.

---

## Part 7 — Ecosystem integration map

```
                        ┌──────────────────────────┐
                        │   agentskills.io schema  │
                        │  (37+ compatible clients)│
                        └─────────────┬────────────┘
                                      │ v3.0 compliance
                                      ▼
  ┌──────────────┐           ┌──────────────────┐           ┌──────────────┐
  │ claude-mem   │◄─ v5.0 ──►│     OpenFang     │◄─ v5.5 ──►│   multica    │
  │   MCP tools  │ parity    │  (this project)  │ runtime   │   8 runtimes │
  └──────────────┘           └────┬───────┬─────┘           └──────────────┘
                                  │       │
                         v3.3 ────┤       ├──── v8 entire
                     trajectory   │       │    (domain-swapped)
                         export   │       │
                                  ▼       ▼
                           ┌──────────┐   ┌───────────┐
                           │  Hermes  │   │  GBrain   │
                           │  Agent + │   │  patterns │
                           │  Atropos │   │           │
                           └──────────┘   └───────────┘
```

| Ecosystem | OpenFang surface | Version | Direction |
| --- | --- | --- | --- |
| agentskills.io | `SKILL.md` + `validate_skill()` + dual-frontmatter parser | v3.0 | bidirectional |
| claude-mem | `memory.search` / `memory.timeline` / `memory.get_observations` | v5.0 | in (we're drop-in replaceable) |
| Hermes Agent | `openfang trace validate` emits Atropos-compatible JSONL | v3.3 | out (we feed their trainer) |
| multica | `MulticaAdapter` listens to task-assignment lifecycle | v5.5 | in (we're the 9th runtime) |
| MCP stdio (v2.6) | 7 read-only tools over JSON-RPC stdio | v2.6, v5.0 | in |
| MCP remote (v8.6) | Same 7 tools over HTTP with Bearer auth + rate limit | v8.6 | in |
| GBrain | Domain-swapped self-wiring + cascades + reconciler + backlink | v8 entire | pattern adoption |

---

## Part 8 — What's genuinely novel

An honest accounting of what OpenFang contributed vs. what it adopted.

### Novel to OpenFang

- **Self-research recursion** (v6.5). OpenFang's narrow domain includes research-agent research. `extract_open_questions()` in [src/open_fang/self_research.py](../src/open_fang/self_research.py) reads every `vN-plan.md` and runs the pipeline on its Open Questions. No other tool in the ecosystem does this.
- **Version-plan docs as load-bearing artifacts.** Every release has a pre-written `vN-plan.md` that names the theme, enumerates workstreams, commits exit criteria. The plans aren't documentation — they're the design-review trail, versioned with the code.
- **Four-corner theme heuristic.** Speaks (v5) → Debugs (v6) → Scales (v7) → Wires (v8). Each version committed to one verb. The heuristic is portable to other agent projects.
- **Claim-kind router** (v4.1). Different claim kinds (quant / qual / citation / methodological) trigger different verifier-tier subsets. The routing matrix is published, tested, and saves ~40% of LLM calls on the 20-brief corpus.
- **TDD-first agent** with rubrics-before-implementation (v1 onwards). Every primitive ships its Claw-Eval-shape rubric JSON before the module exists. 612 tests and counting.
- **BrainBench-analog on our own corpus** (v8.5). We don't copy GBrain's numbers — we compute ours on our own 20-paper corpus and publish whatever we measure.

### Adopted / adapted from the ecosystem (all credited in Part 5)

- SemaClaw (arxiv:2604.11548): DAG-teams + PermissionBridge + persona partition.
- Atomic Skills (arxiv:2604.05013): mutation-robust verifier, atomic-skill taxonomy idea.
- Agent-World (arxiv:2604.18292): evolving arena, graph-walk brief synthesis, Vcode executable verifier.
- Corpus2Skill (arxiv:2604.14572): skill-tree navigation pattern.
- everything-claude-code (affaan-m/everything-claude-code): SKILL.md format + `/skill-create` pipeline shape.
- nousresearch/hermes-agent: agentskills.io compliance, Atropos RL export target.
- thedotmack/claude-mem: progressive-disclosure memory architecture (clean-room — AGPL).
- multica-ai/multica: task-assignment lifecycle.
- garrytan/gstack: 9-specialist cohort, 3-mode cross-model verification, Conductor pattern.
- garrytan/gbrain: self-wiring KG, typed-edge cascades, reconciler, backlink boost.
- QMD (tobi/qmd): BM25 + dense + RRF + reranker.
- claude-context (zilliztech): AST + Merkle-tree incremental index.
- Context Mode (mksglu): tool-output sandboxing.
- alexgreensh token-optimizer (clean-room, PolyForm-NC): degradation monitor, loop detector, delta mode.
- Token Savior (Mibayy): Bayesian validity + contradiction detection.
- Caveman (JuliusBrussee): output compression profiles.

Every pattern above shipped with a docstring citing its source. Clean-room boundaries for PolyForm-NC code are documented per-module.

---

## Part 9 — Further improvements + open research

Broken into near-term, medium-term, and speculative horizons.

### Near-term (v9 candidates)

- **LLM-semantic cascade rules** beyond v8's depth-1 × 4 static rules. An LLM-judged rule matcher over existing edges can propose new typed edges; the reconciler gates them by confidence. Budget ~2-3 workstreams.
- **Real-time OpenTelemetry span export.** Gnomon spans already exist; adding OTLP export turns OpenFang into a first-class observable agent in any OTLP-consuming stack.
- **PDF-parse path for arxiv full-text.** Currently abstract-only. A LaTeX source parser would unlock reference-list edges (v8.0's author-year regex has limited recall without the full body).
- **Larger BrainBench corpus.** 20 papers is a baseline. Growing to 100+ lets us publish ablations per workstream.
- **Atropos trajectory ingestion tests** against a real Hermes submodule fixture. v3.3 ships the format; v9 verifies against real Hermes expectations.

### Medium-term (v10–v11)

- **Multi-tenant KB with per-user partitions.** SQLite+FTS5 is single-writer; above 100k papers or multi-user shared deployment, migrate to Postgres+pgvector (the GBrain alternative we held off on).
- **Federated research across multiple OpenFang instances.** Two instances share their citation graphs + self-wired edges; RRF fusion across partitions.
- **RL training loop using Atropos export.** v3.3 emits the trajectories; Hermes consumes them; future OpenFang model variants trained on our own outputs.
- **Voyager-style skill self-modification.** v2.1 ships the evolving arena; a v10 extension lets skills mutate their own SKILL.md based on trajectory corroboration.
- **Cross-family reasoning for high-risk claims** beyond v4.2's 3 modes — chain 3+ different model families for consensus on mutation-flagged claims.

### Speculative (v12+)

- **Proof-carrying claims.** Cryptographic signatures over (claim, evidence_ids, verifier_passes). A Report becomes cryptographically auditable — any consumer can verify claim-evidence binding without re-running the pipeline.
- **Agent-to-agent research debate.** Two OpenFang instances tasked with opposing positions, their outputs adjudicated by a third. Useful for contested literature (e.g., scaling-laws debates).
- **Recursive-depth reasoning models** when open-weights ship (see [docs/32-recurrent-depth-implicit-reasoning.md](../../docs/32-recurrent-depth-implicit-reasoning.md)). Model-level iteration at inference time replaces token-level CoT for deep reasoning.
- **Ghost-author detection.** Scan authors + affiliations + writing style across the KB; flag papers whose author list seems inconsistent with prior work.
- **Full Gnomon implementation** (see [docs/67-recommended-breakthrough-project.md](../../docs/67-recommended-breakthrough-project.md)). HAFC-lite is v6.0's shipped shape; the full HIR + HAFC + SHP stack would make primitive-level attribution a trained classifier with cross-agent portability.

### Open questions that v6.5 self-research found

Each `vN-plan.md` has an Open Questions section; the self-research loop extracts them; many remain:

- **Embedding model default** — HF `bge-small-en` vs OpenAI `text-embedding-3-small`? Our v7.1 default is HF for offline-first; prod deployers may prefer OpenAI.
- **Reranker model default** — Qwen3-reranker-0.6b is QMD's choice. Opt-in only until we see measurable wins on our corpus.
- **Claim-kind router tolerance** — ±15% default in Tier 4.5 symbolic; may be too loose for strict claims.
- **Cascade depth** — v8.1 is depth-1. Depth-2 risks edge explosion; measure on realistic corpora first.
- **HAFC primitive count** — 12 today. Should it split `synthesis` into `claim-generation` vs `evidence-binding`? Monitor attribution ambiguity rate.

---

## Part 10 — How to read the code + glossary

### Navigation guide

> "If you want to understand X, start at Y, read Z."

| Goal | Entry point | Next files |
| --- | --- | --- |
| Understand the full pipeline | [src/open_fang/pipeline.py](../src/open_fang/pipeline.py) | [scheduler/engine.py](../src/open_fang/scheduler/engine.py), [verify/claim_verifier.py](../src/open_fang/verify/claim_verifier.py) |
| Understand a Brief→Report run | [tests/integration/test_pipeline_happy_path.py](../tests/integration/test_pipeline_happy_path.py) | [models.py](../src/open_fang/models.py), [synthesize/writer.py](../src/open_fang/synthesize/writer.py) |
| Understand verification | [verify/claim_verifier.py](../src/open_fang/verify/claim_verifier.py) | Each tier in its own file under `verify/` |
| Understand the KB | [kb/store.py](../src/open_fang/kb/store.py) | [kb/schema.sql](../src/open_fang/kb/schema.sql), then [kb/promote.py](../src/open_fang/kb/promote.py), [kb/self_wire.py](../src/open_fang/kb/self_wire.py) |
| Understand the skill library | [skills/schema.py](../src/open_fang/skills/schema.py) | [skills/loader.py](../src/open_fang/skills/loader.py), [skills/registry.py](../src/open_fang/skills/registry.py), `skills/*/SKILL.md` |
| Understand specialists | [supervisor/specialist.py](../src/open_fang/supervisor/specialist.py) | [supervisor/registry.py](../src/open_fang/supervisor/registry.py) |
| Understand failure attribution | [attribution/primitives.py](../src/open_fang/attribution/primitives.py) | [attribution/classifier.py](../src/open_fang/attribution/classifier.py) |
| Understand memory | [memory/store.py](../src/open_fang/memory/store.py) | [memory/progressive.py](../src/open_fang/memory/progressive.py), [memory/fang.py](../src/open_fang/memory/fang.py) |
| Understand ecosystem adapters | [mcp_server/server.py](../src/open_fang/mcp_server/server.py) | [adapters/multica.py](../src/open_fang/adapters/multica.py), [trace/export.py](../src/open_fang/trace/export.py) |

### Glossary (50 terms)

- **AGENTS.md** — universal entry point at repo root; ECC convention adopted in v2.7.
- **agentskills.io** — open `SKILL.md` schema supported by 37+ agent clients; OpenFang compliant since v3.0.
- **attribution** — assigning a failure to one of 12 named primitives (v6.0 HAFC-lite).
- **Bayesian validity** — beta-binomial update on a memory observation's trust score (v7.3).
- **BrainBench** — GBrain's graph-retrieval benchmark. OpenFang's v8.5 analog runs on our 20-paper corpus.
- **brief** — the user's input; a research question plus cost + length preferences.
- **cascade rule** — depth-1 typed-edge inference rule on the KB (v8.1).
- **Caveman** — garrytan-adjacent output-compression pattern adopted in v7.6.
- **chaos hook** — env-configured fault injector in the scheduler (v2.5).
- **claim** — an evidence-bound statement; always carries `evidence_ids[]`.
- **claim kind** — quantitative / qualitative / citation / methodological (v4.1 router).
- **Claw-Eval** — benchmark discipline (Pass@k + Pass^k, three evidence channels) adopted v1.6.
- **cohort** — the 9-specialist roster (v4.0).
- **Conductor** — gstack pattern of 10-15 isolated Claude Code sessions; OpenFang's v4.3 analog is `IsolatedSupervisor`.
- **cross-model verify** — three-mode pattern (review / adversarial / consultation) from gstack `/codex`.
- **DAG-teams** — SemaClaw pattern: LLM planner → deterministic scheduler.
- **decontamination** — scan KB for benchmark-set fingerprints (Atomic Skills App. C.1, v2.7).
- **degradation signal** — one of 7 grades (S-F) that `DegradationMonitor` tracks (v7.2).
- **delta mode** — re-read returns stub with hash (v7.4).
- **Diagnostician** — distinct from CriticAgent; reads a cohort of failed runs and emits guidelines (v2.1).
- **Evidence** — snippet + source-ref + channel + optional structured_data.
- **evolving arena** — one-round loop: run → diagnose → extract skills (v2.1).
- **FANG.md** — persona partition, size-capped, never compacted.
- **feed cron** — opt-in weekly awesome-list puller (v5.4).
- **HAFC** — Harness-Aware Failure Classifier; lite version shipped v6.0.
- **HIR** — Harness-Intermediate Representation; full Gnomon concept (not shipped).
- **hybrid search** — BM25 + dense + RRF in v7.1.
- **InferredEdge** — self-wired edge with confidence + pattern-name + provenance (v8.0).
- **lifecycle stage** — plan / retrieve / extract / verify / synthesize / critique / publish (v4.4).
- **loop detector** — short-circuits repeat `(kind, args)` dispatches (v7.2).
- **MCP** — Model Context Protocol; stdio server v2.6, HTTP+Bearer v8.6.
- **MemoryStore** — SQLite-backed progressive-disclosure observation log (v3.1).
- **Merkle tree** — sentence-chunk hash tree for incremental reindex (v7.5).
- **multica** — 18.3k-star multi-agent runtime platform; adapter in v5.5.
- **PermissionBridge** — runtime-enforced risk gate (v1.5).
- **primitive** — one of 12 canonical pipeline stages (v6.0 attribution vocabulary).
- **PromotionReport** — KB write output (papers_added / claims_added / skipped_* counts).
- **provenance** — load-bearing edge-row column; `self-wire:*` vs manual (v8 CC-1).
- **reconciler** — expires stale self-wired edges on re-upsert (v8.3).
- **RRF** — Reciprocal Rank Fusion (k=60, QMD default).
- **sandbox handle** — FTS5-indexed deferred tool output (v7.0).
- **self-wire** — zero-LLM regex citation extraction on upsert (v8.0).
- **SKILL.md** — agentskills.io-compliant skill declaration.
- **skill tree** — hierarchical skill organization, max depth 3, max 12 leaves per category (v5.1).
- **Span** — Gnomon-shape observability record per node.
- **specialist** — role-scoped dispatch unit with owned skills + verifier tiers + model-family preference.
- **stage** — v4.4 lifecycle label on a span.
- **symbolic verifier** — Tier 4.5 numeric-assertion check (v6.2).
- **token budget** — implicit throughout v7; bounded-cost as first-class metric.
- **verifier tier** — one of 5 (or 6 with Tier 4.5) claim-verification layers.

---

## Appendix A — Source file index

Every Python module under `src/open_fang/` mapped to the Book section that covers it most fully.

### Top-level

| File | Covered in |
| --- | --- |
| [`__init__.py`](../src/open_fang/__init__.py) | Part 3 |
| [`models.py`](../src/open_fang/models.py) | Part 2 + 4 |
| [`pipeline.py`](../src/open_fang/pipeline.py) | Part 3 |
| [`app.py`](../src/open_fang/app.py) | Part 4.12 |
| [`cli.py`](../src/open_fang/cli.py) | Part 10 |
| [`chaos_scanner.py`](../src/open_fang/chaos_scanner.py) | Part 4.12 |
| [`self_research.py`](../src/open_fang/self_research.py) | Part 8 |

### planner/, scheduler/, sources/

| File | Covered in |
| --- | --- |
| [`planner/llm_planner.py`](../src/open_fang/planner/llm_planner.py) | 4.1 |
| [`planner/schema.py`](../src/open_fang/planner/schema.py) | 4.1 |
| [`planner/replanner.py`](../src/open_fang/planner/replanner.py) | 4.1 |
| [`scheduler/engine.py`](../src/open_fang/scheduler/engine.py) | 4.2 |
| [`scheduler/parking.py`](../src/open_fang/scheduler/parking.py) | 4.2 |
| [`scheduler/retries.py`](../src/open_fang/scheduler/retries.py) | 4.2 |
| [`scheduler/chaos.py`](../src/open_fang/scheduler/chaos.py) | 4.2 |
| [`scheduler/loop_detector.py`](../src/open_fang/scheduler/loop_detector.py) | 4.2 |
| [`sources/*`](../src/open_fang/sources/) | 4.3 |

### verify/, synthesize/

| File | Covered in |
| --- | --- |
| [`verify/claim_verifier.py`](../src/open_fang/verify/claim_verifier.py) | 4.4 |
| [`verify/llm_judge.py`](../src/open_fang/verify/llm_judge.py) | 4.4 |
| [`verify/mutation.py`](../src/open_fang/verify/mutation.py) | 4.4 |
| [`verify/executable.py`](../src/open_fang/verify/executable.py) | 4.4 |
| [`verify/symbolic.py`](../src/open_fang/verify/symbolic.py) | 4.4 |
| [`verify/critic.py`](../src/open_fang/verify/critic.py) | 4.4 |
| [`verify/cross_model.py`](../src/open_fang/verify/cross_model.py) | 4.4 |
| [`verify/router.py`](../src/open_fang/verify/router.py) | 4.4 |
| [`verify/halt.py`](../src/open_fang/verify/halt.py) | 4.4 |
| [`verify/redteam.py`](../src/open_fang/verify/redteam.py) | 4.12 |
| [`synthesize/writer.py`](../src/open_fang/synthesize/writer.py) | 4.5 |
| [`synthesize/compression.py`](../src/open_fang/synthesize/compression.py) | 4.5 |

### kb/, memory/

All `kb/*` files covered in 4.6. All `memory/*` files covered in 4.7.

### supervisor/, permissions/, observe/, skills/

All `supervisor/*` files covered in 4.11. All `permissions/*` in 4.8. All `observe/*` in 4.9. All `skills/*` in 4.10.

### attribution/, mcp_server/, trace/, adapters/, eval/, security/

All covered in 4.12.

---

## Appendix B — Test catalog

612 tests across 3 tiers:

- **Unit** — `tests/unit/test_*.py` — ~55 files, ~450 tests. ≤ 50ms per test. Target ≥ 85% line coverage.
- **Integration** — `tests/integration/test_*.py` — ~12 files, ~60 tests. Full pipeline paths, mock-sourced.
- **Evaluation** — `tests/evaluation/test_*.py` — ~8 files, ~100 tests. SLO-gated: faithfulness ≥ 0.90, Pass^5 ≥ 0.70, mutation resistance ≥ 0.85, security catch ≥ 0.80, token reduction ≥ 5×.

Plus 1 network-marked test ([tests/integration/test_dogfood_arxiv.py](../tests/integration/test_dogfood_arxiv.py)) deselected in CI (`pytest -m network` runs it).

Fixtures:
- [`tests/fixtures/paper_data.py`](../tests/fixtures/paper_data.py) — 5 canonical papers.
- [`tests/fixtures/briefs.py`](../tests/fixtures/briefs.py) — 50-brief eval corpus.
- [`tests/fixtures/mutation_claims.py`](../tests/fixtures/mutation_claims.py) — 10-case mutation corpus.
- [`tests/fixtures/security_briefs.py`](../tests/fixtures/security_briefs.py) — 10 adversarial cases.

Running the suite:

```bash
make install          # venv + deps
make test             # pytest (612 + 1 network-deselected)
make lint             # ruff
.venv/bin/pytest -m network  # include the dogfood arxiv test
```

---

## Appendix C — Planning document lineage

OpenFang is planned-before-coded. Every version's theme, workstreams, trade-offs, and exit criteria live in a markdown file committed before the implementation.

| Version | Plan | Theme | Released as |
| --- | --- | --- | --- |
| v1 | [plan.md](../plan.md) | TDD scaffold + 5-tier verifier | 129 tests |
| v2 | [v2-plan.md](../v2-plan.md) | Skills + KB graph + security + MCP | 305 tests |
| v3 | [v3-plan.md](../v3-plan.md) | Interop + progressive memory + specialists | 368 tests |
| v4 | [v4-plan.md](../v4-plan.md) | 9-role cohort + cross-model + stage labels | 402 tests |
| v5 | [v5-plan.md](../v5-plan.md) | **Speaks** — ecosystem interop | 425 tests |
| v6 | [v6-plan.md](../v6-plan.md) | **Debugs** — primitive-level attribution | 478 tests |
| v7 | [v7-plan.md](../v7-plan.md) | **Scales** — bounded token cost | 547 tests |
| v8 | [v8-plan.md](../v8-plan.md) | **Wires** — self-populating KG | 612 tests |

Each plan contains: §0 TL;DR, §1 research inputs, §2 goals/non-goals, §3 workstreams, §4 cross-cutting concerns, §5 phases, §6 trade-offs, §7 risks, §8 open questions, §9 one-sentence pitch.

This lineage itself is part of the project. Future maintainers reading plan.md → v2-plan.md → v3-plan.md see not just what was built but why each choice was made and what was considered-then-rejected. The Open Questions sections feed the v6.5 self-research loop, closing the design-review cycle.

---

## Closing note

OpenFang is a working autonomous AI research agent at v8.7 with 612 passing tests, specialized for AI / Agentic AI / Harness Engineering literature. It **speaks** every ecosystem's wire format, **debugs** its own failures at primitive granularity, **scales** by holding token cost as a first-class metric, and **wires** its own knowledge graph without ever calling an LLM for the graph layer.

Everything in this Book is anchored in code under `src/open_fang/` and verified by tests under `tests/`. If a claim here ever disagrees with the tests, the tests win — update the Book.

*End of document.*
