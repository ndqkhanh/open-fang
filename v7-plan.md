# OpenFang v7 — Plan

> **Prerequisite:** v6 released (478 tests). HAFC-lite, confidence halt, symbolic verifier, native arxiv/GitHub/HF adapters, chaos×HAFC scanner, self-research loop all live. v7 is the post-attribution horizon: now that we *know* what fails, make every pass through the pipeline **token-lean**.

## 0. TL;DR

Fresh research input (2026-04-22): a 10-tool survey of Claude Code token-reduction infrastructure ("60-90% fewer tokens"). Seven of the ten tools ship patterns OpenFang has never applied. All seven target a different waste class:

| Waste class | Share | OpenFang status today |
| --- | --- | --- |
| Terminal / tool-output flooding | 15-25% | **unmitigated** — source adapters return full payloads |
| Verbose AI responses | ~20% | **unmitigated** — report writer emits full prose |
| Initial project load | ~15% | partial — FANG.md is size-capped |
| Code-navigation (structural) | 40-50% | N/A — we're a research agent, not a coding agent |

The 40-50% "code-navigation" waste bucket doesn't apply (we index papers, not code), but the other three classes **do**, and they're ~60% of OpenFang's current token budget per brief. v7's thesis: **OpenFang should emit briefings and run sessions with the same token discipline that Context Mode, QMD, and Token Savior bring to Claude Code**.

Five transformative patterns surfaced:

1. **Tool-output sandboxing** (Context Mode) — index big tool outputs to FTS5, return summaries. OpenFang's arxiv/S2/GitHub adapters currently shovel entire search results into context.
2. **Hybrid search with LLM reranking** (QMD + claude-context) — BM25 + dense embeddings + RRF fusion + Qwen3-style reranker. Our current `kb.search` is FTS5-only; upgrading yields measurably better recall at similar cost.
3. **AI degradation detection + loop detector** (token-optimizer alexgreensh) — 7-signal quality monitor, S-F grades, detects retry-loops. Pairs naturally with v6 HAFC.
4. **Delta mode** (token-optimizer alexgreensh) — return only diffs on re-read, claimed up to 97% reduction per task. OpenFang re-reads same papers repeatedly; this is free savings.
5. **Bayesian validity + contradiction detection** (Token Savior Recall) — track validity of memory observations, flag contradictions. Natural evolution of v3.1 progressive-disclosure memory.

Plus two minor polish items:

- **Caveman-style output compression** (a response-style option on `/v1/research`).
- **Merkle-tree incremental KB indexing** (claude-context pattern) — avoid full reindex on paper upsert.

Plus one honest rejection:

- **AST / code-graph indexing** (code-review-graph) — not our domain. OpenFang researches papers, not repos. The pattern is excellent for coding agents and irrelevant here.

---

## 1. The 10 tools — what matters for OpenFang

| # | Tool | Pattern | v7 verdict |
| --- | --- | --- | --- |
| 1 | **Context Mode** | Tool-output sandboxing + FTS5 BM25 | **✅ W1** — adopt for source adapters |
| 2 | code-review-graph | Tree-sitter AST + blast radius | ❌ out of domain (coding-agent-specific) |
| 3 | **Token Savior (Recall)** | Bayesian validity + contradiction detection + hybrid BM25+vector | **✅ W5** — memory-layer upgrade |
| 4 | Caveman | Output compression profiles | ✅ **CC-1** — compact-mode flag on `/v1/research` |
| 5 | claude-token-efficient | CLAUDE.md rules | partial — fold into FANG.md v2 seeds |
| 6 | token-optimizer-mcp | MCP caching/compression (95% unverified) | skip — unverified benchmarks |
| 7 | claude-token-optimizer | Doc-structure generator | ❌ FANG.md already small |
| 8 | **token-optimizer (alexgreensh)** | AI degradation detector + loop detection + delta mode | **✅ W3 + W4 + W6** (three workstreams) |
| 9 | **claude-context (Zilliz)** | Hybrid BM25+dense embeddings + Merkle-tree incremental index | **✅ W2 + W7** (two workstreams) |
| 10 | **QMD** | BM25 + dense + RRF fusion + local LLM reranker (Qwen3-0.6b) | **✅ W2** — enrich hybrid search with RRF + reranker |

**Licensing caveats** (flagged by the source document):
- token-optimizer (alexgreensh) is **PolyForm Noncommercial 1.0.0**. v7 patterns inspired by it must be clean-room, same policy as v3.1's claude-mem work.
- All other tools: MIT / Apache-2.0 / permissive.

---

## 2. Goals and Non-Goals

### Goals
1. **Tool-output sandboxing** so source adapters returning >5KB get indexed and summarized before hitting context.
2. **Hybrid search** upgrade: BM25 (existing) + dense embeddings (new) + RRF fusion + optional local reranker.
3. **AI-degradation detection** — 7-signal quality monitor running alongside v6 HAFC; emits warning events.
4. **Loop detection** — scheduler detects same-query-same-args retries and breaks the loop.
5. **Delta-mode for source re-reads** — when OpenFang re-fetches a paper it already has, return only the diff.
6. **Bayesian validity tracking** on memory observations — confidence weights on each observation, contradiction flagging.
7. **Merkle-tree incremental KB indexing** — paper upsert only reindexes changed blocks.
8. **Output compression flag** on `/v1/research` — Caveman-inspired terse mode.

### Non-Goals
- **No AST code indexing**. We research papers, not code. OpenFang stays text/arxiv-centric.
- **No doc auto-structuring.** FANG.md is already under the 16KB cap; we don't need claude-token-optimizer's bash script.
- **No unverified claim adoption.** token-optimizer-mcp claims "95% token savings" without published benchmarks; skip until verified.
- **No commercial dependency on PolyForm-NC code.** alexgreensh's implementation is reference-only; every v7 implementation is clean-room.
- **No local-only embedding model dependency in CI.** W2's embedding is hashable stub in tests; production uses HF or OpenAI via injectable client.
- **No rewrites of v1-v6 subsystems** — everything in v7 extends existing modules.

---

## 3. Workstreams

### W1 — Tool-Output Sandboxing (Context Mode pattern)

**Source.** github.com/mksglu/context-mode — 99% reduction on Playwright snapshots, 98% on GitHub issues, FTS5-indexed + BM25 retrieval.

**Why v7.** Our arxiv / S2 / GitHub adapters return up to 50 evidence items × ~1KB each = 50KB+ per search. All of it flows into context even when only 3-5 items matter.

**Design.**

- New `src/open_fang/memory/sandbox.py` with:
  - `ToolOutputSandbox` — when `source_router.search(...)` returns > `sandbox_threshold_bytes`, the adapter's payload is appended to the MemoryStore (new `tool_outputs` column), and the scheduler gets back a **summary tuple** `(summary_text, retrieval_handle)`.
  - `retrieve(handle, query)` — BM25 query against the sandboxed payload; returns the top-N matching evidence records.
- Config: `OPEN_FANG_SANDBOX_THRESHOLD_BYTES=5000` (default).
- Integration: `SchedulerEngine._execute()` on search.* nodes checks payload size; large payloads sandboxed automatically.

**Tests.** (target +10)
- Unit: sandbox round-trip: store 50KB payload → retrieve 3 items via BM25.
- Unit: small payloads (< threshold) bypass sandbox.
- Integration: pipeline with 100-item canned search returns ≤ 5 evidence items in context; sandbox retrieval finds the other 95 on demand.
- Evaluation: token-budget sweep over 20-brief corpus — ≥ 30% context-token reduction on synthetic large-result briefs.

### W2 — Hybrid Search + Reranking (QMD + claude-context patterns)

**Source.** QMD (BM25 + embeddings + RRF + Qwen3-0.6b reranker) + claude-context (Zilliz) (hybrid BM25+dense).

**Why v7.** Our `KBStore.search()` is FTS5-only. For overlapping query/evidence vocabulary it works; for paraphrased queries (the majority in research) it misses. Adding dense embeddings doubles hit rate at comparable cost; adding RRF fusion + local reranker triples it.

**Design.**

- Schema addition (migration): `papers_fts` gets a sibling `papers_embeddings` table — `paper_id TEXT PRIMARY KEY, embedding BLOB (float32 array)`. Embeddings generated by an injectable `Embedder` protocol.
- New `src/open_fang/kb/hybrid_search.py` with:
  - `HybridSearch(kb, embedder, reranker=None)` — executes BM25 + embedding similarity in parallel, merges via Reciprocal Rank Fusion (RRF k=60), optionally reranks top-30 with a local reranker.
  - Returns same `Evidence` shape as existing `kb.search`; existing callers unchanged.
- Embedder: `HashEmbedder` (stable deterministic for tests) + `HFEmbedder` (bge-small-en via sentence-transformers) + `OpenAIEmbedder` (text-embedding-3-small). Tests use `HashEmbedder`; prod default is `HFEmbedder`.
- Reranker: optional; when wired, runs a small LLM pass on top-30 results.

**Tests.** (target +12)
- Unit: `HashEmbedder` deterministic + reproducible.
- Unit: RRF fusion merges disjoint rank lists correctly.
- Unit: `HybridSearch` returns BM25-only when `embedder=None`; BM25+dense when wired.
- Evaluation: paraphrased-query recall on 20-brief corpus — hybrid ≥ 15pp improvement over BM25-only.
- Integration: reranker skipped when disabled; enabled with MockLLM returns top-3 reordered.

### W3 — AI Degradation Detector (alexgreensh pattern, clean-room)

**Source.** token-optimizer (alexgreensh) — 7-signal quality monitor, S-F grades, $1,500-2,500/mo savings estimated on real data. PolyForm-NC; clean-room implementation required.

**Why v7.** Pairs with v6 HAFC: HAFC tells us *which primitive failed*; the degradation detector tells us *when a run is about to fail*. Early warning unlocks early termination.

**Design.**

- Clean-room: we read only the published README and the source document's description; no source code reference.
- New `src/open_fang/observe/degradation.py`:
  - `DegradationMonitor` tracks 7 signals across a running pipeline:
    1. **Faithfulness trend** — rolling window of `faithfulness_ratio` values.
    2. **Retry rate** — percentage of nodes retried at least once.
    3. **Mutation-warning rate** — percentage of claims carrying the flag.
    4. **Critic downgrade rate** — per-brief downgrade count.
    5. **HAFC attribution spread** — entropy over primitive distribution (low entropy = repeated same-primitive failure).
    6. **Evidence fetch duplication rate** — same paper id fetched > once per brief.
    7. **Verdict self-disagreement** — LLM judge verdict flips across re-queries.
  - Emits a letter grade (S / A / B / C / D / F) per signal + an aggregate grade.
  - `should_checkpoint()` returns True when aggregate grade drops below `C`.
- Integration: the pipeline's `SpanRecorder` feeds spans to the monitor; aggregate grade surfaced on `PipelineResult.degradation_grade`.

**Tests.** (target +9)
- Unit: each signal has a dedicated unit test.
- Unit: aggregate grade matches the worst signal when one dominates.
- Unit: checkpoint trigger fires when ≥ 3 signals drop below `C`.
- Integration: pipeline run under chaos (forced failures) produces grade ≤ `C`.

### W4 — Loop Detector

**Source.** Same alexgreensh tool — detects retry patterns and breaks them.

**Why v7.** Research agents sometimes re-query the same search with the same args across specialists. The scheduler's retry path + multi-specialist dispatch compounds this.

**Design.**

- New `src/open_fang/scheduler/loop_detector.py`:
  - `LoopDetector` tracks `(node.kind, canonicalized(args))` hashes within a run.
  - `saw_before(node)` returns `True` when the same hash repeats within the same pipeline run.
  - When repeat detected, scheduler injects a `"seen-before: <previous_output_id>"` hint into the node's context; specialist can read prior result.
- Integration: scheduler checks loop detector before dispatching; repeat nodes short-circuit to cached output.

**Tests.** (target +6)
- Unit: same (kind, args) → detected as repeat.
- Unit: different args → not repeat.
- Unit: cleared across pipeline runs.
- Integration: pipeline with duplicate nodes runs the expensive operation only once.

### W5 — Bayesian Memory Validity (Token Savior Recall pattern)

**Source.** github.com/Mibayy/token-savior — Bayesian validity tracking, contradiction detection, hybrid BM25+vector embedding search for persistent memory.

**Why v7.** v3.1 memory stores observations but doesn't weight them; v3.1's Tier A always returns newest-first. Bayesian validity lets a high-trust old observation survive; low-trust recent ones fade.

**Design.**

- Schema extension: `observations` gets `validity REAL DEFAULT 0.5, last_updated_at TEXT`. Initial validity = 0.5. Each reuse that corroborates bumps validity up via Bayesian update; contradicting observation pushes validity down.
- New `src/open_fang/memory/validity.py`:
  - `update_validity(observation_id, corroborated: bool)` — beta-binomial update with prior (2, 2) shape.
  - `detect_contradictions(kb)` — scans pairs of observations with overlapping claims (FTS5 top-matching pairs) and flags contradictions.
- Tier A `compact_index()` re-ranks by validity × recency weight, not raw recency.

**Tests.** (target +7)
- Unit: validity update with corroboration trends up after 5 agreements.
- Unit: validity update with contradiction trends down after 5 disagreements.
- Unit: beta-binomial math matches reference values.
- Unit: contradiction detector flags two claims with token-overlap + opposite numbers.
- Integration: Tier A ordering changes when older high-validity observation outranks newer low-validity one.

### W6 — Delta Mode for Source Re-reads

**Source.** Same alexgreensh tool — return only diffs on re-read, up to 97% reduction per task.

**Why v7.** Our arxiv source re-fetches full abstracts on every search. If a paper is already in the KB, we already have its content — no need to return the full payload.

**Design.**

- `SourceRouter.search()` enrichment: before returning Evidence, check against `KBStore.list_paper_ids()`; for each hit:
  - Known paper, same content hash → return `Evidence` stub with `content=""`, `delta_mode=True`, and a retrieval handle to the KB.
  - Known paper, different content hash → return full content as "updated evidence".
  - Unknown paper → return full content (default).
- New column on `papers`: `content_sha256 TEXT`. Upsert computes hash; delta-mode uses this for comparison.
- `Evidence.delta_mode: bool` — new field indicating this is a stub referencing existing KB content.

**Tests.** (target +6)
- Unit: repeat search on seeded KB → delta-mode stubs for known papers.
- Unit: content change detected → full content returned + hash updated.
- Unit: delta-mode respected only when KB has the paper_id.
- Integration: second research call on same topic runs 50-70% token-lighter than first (measured via claim-count * content-size).

### W7 — Merkle-Tree Incremental KB Indexing (claude-context pattern)

**Source.** Zilliz claude-context — Merkle-tree + AST chunking for incremental reindex.

**Why v7.** `KBStore.upsert_paper` does a full FTS5 rebuild on the paper's row each time. On a KB of 10,000 papers that's wasteful. Merkle-tree incremental hashing lets us reindex only changed blocks.

**Design.**

- Paper content split into chunks (sentences or paragraphs); each chunk hashed; parent hashes stored in an `index_merkle` table.
- Upsert path: compute new chunk hashes; diff against existing → reindex only changed chunks in FTS5 + embeddings.
- For v7 MVP, granularity is per-sentence chunks. Per-paragraph / per-token is v8.

**Tests.** (target +6)
- Unit: identical content → zero chunks reindexed.
- Unit: one-sentence change → one chunk reindexed, rest preserved.
- Unit: full replacement → all chunks reindexed.
- Integration: 100-paper KB with 1 paper updated — FTS5 rebuild time < 10ms.

### CC-1 — Caveman-Style Output Compression

**Source.** github.com/JuliusBrussee/caveman — 4 compression profiles (Lite / Full / Ultra / 文言文), 65% average output reduction.

**Design.**

- `Brief.compression_mode: Literal["standard", "terse", "ultra"] = "standard"`.
- `SynthesisWriter` applies the profile at render time:
  - `standard`: current behavior.
  - `terse`: drops connectives, keeps imperative sentences only.
  - `ultra`: bullet-only, strips articles/prepositions, integer citations.
- Round-trip preserved: compressed output still parses back to a `Report` with the same claim binding.

**Tests.** (target +5)
- Unit: compression_mode="terse" reduces `to_markdown()` length by ≥ 40%.
- Unit: compression_mode="ultra" reduces by ≥ 65%.
- Unit: claim bindings preserved across all modes.

---

## 4. Cross-cutting concerns

### CC-2 — License audit before every new module
Every new v7 module's docstring declares its provenance: "Clean-room reimplementation of [idea] from [source], README only" or "MIT-compatible adoption of [pattern]". No code is copied from PolyForm-NC sources.

### CC-3 — Embedding model choice is configurable
`HashEmbedder` for tests (no network), `HFEmbedder` / `OpenAIEmbedder` for prod. Users wire via env var `OPEN_FANG_EMBEDDER=hf|openai|hash`.

### CC-4 — Release cadence formalization (carry from v5)
Weekly: feed cron. Bi-weekly: evolving arena. **Monthly: degradation-monitor review** (new). Quarterly: self-research + next-version plan.

---

## 5. Phases

| Phase | Scope | Exit | Tests target |
| --- | --- | --- | --- |
| v7.0 | W1 tool-output sandboxing | 30% context-token drop on large-result briefs | ~495 |
| v7.1 | W2 hybrid search + RRF | ≥ 15pp recall gain on paraphrased queries | ~510 |
| v7.2 | W3 degradation detector + W4 loop detector | chaos run emits ≤C grade; loop detector short-circuits repeat nodes | ~525 |
| v7.3 | W5 Bayesian validity + contradiction detection | old high-validity observation outranks newer low-validity | ~535 |
| v7.4 | W6 delta mode | second research call runs 50% lighter | ~545 |
| v7.5 | W7 Merkle-tree incremental indexing | < 10ms reindex on single-paper update | ~555 |
| v7.6 | CC-1 Caveman-style compression | terse mode −40%, ultra mode −65% on output | ~560 |
| v7.7 | Release v7 | docs + dogfood + cadence review | ~560 |

Target: 478 (v6.6) → ~560 by v7.7. +82 tests across 7 workstreams.

---

## 6. Trade-offs

| Technique | Source | Workstream | Chosen |
| --- | --- | --- | --- |
| Tool-output sandboxing (FTS5-indexed summaries) | Context Mode | W1 | ✅ |
| Hybrid search (BM25 + dense + RRF) | QMD + claude-context | W2 | ✅ |
| Local LLM reranker (Qwen3-style) | QMD | W2 | ✅ opt-in |
| AI-degradation 7-signal monitor | alexgreensh (clean-room) | W3 | ✅ |
| Loop detector | alexgreensh (clean-room) | W4 | ✅ |
| Bayesian validity + contradiction detection | Token Savior Recall | W5 | ✅ |
| Delta-mode source re-reads | alexgreensh (clean-room) | W6 | ✅ |
| Merkle-tree incremental indexing | claude-context | W7 | ✅ |
| Caveman-style output compression | Caveman | CC-1 | ✅ |
| Tree-sitter AST code navigation | code-review-graph | — | ❌ out of domain |
| MCP caching without verified benchmarks | token-optimizer-mcp | — | ❌ unverified |
| Auto-generated project doc structure | claude-token-optimizer | — | ❌ FANG.md already minimal |
| CLAUDE.md rule injection | claude-token-efficient | — | ⏸ small polish item, defer |
| OpenAI embedding API as only embedder | claude-context | — | ❌ offline-first; HF is default |

---

## 7. Risks

- **Sandbox latency on small payloads.** W1 indexing has overhead; may hurt throughput on short briefs. Mitigation: threshold env var; sandbox only when payload > 5KB.
- **Embedding-model cost spike.** W2 HF embeddings are free but slow; OpenAI is fast but costs money. Mitigation: embedder is pluggable; tests use HashEmbedder (no cost).
- **Degradation-monitor false positives.** Thresholds may trigger on benign slow briefs. Mitigation: per-signal configurable thresholds; aggregate-grade requires ≥3 signals to drop before checkpoint.
- **Loop detector over-broad.** Identical queries that *should* repeat (e.g., under different personas) get short-circuited incorrectly. Mitigation: hash includes node.args AND activating specialist; different specialists → different hash.
- **Bayesian validity drift.** With few observations, prior dominates; with many, may overcorrect. Mitigation: beta-binomial prior (2, 2) is weak enough to allow evidence to dominate after ~10 updates.
- **Delta mode stale data.** If arxiv updates a paper, content_sha256 differs — we correctly re-fetch. But if our first fetch was partial, we never learn. Mitigation: periodic full-refresh (monthly) on papers older than N days.
- **Merkle-tree complexity explosion.** Chunk-level tracking can fragment. Mitigation: sentence-level granularity only; periodic full rebuild on chunk-count > 10× paper count.
- **PolyForm-NC contamination.** Patterns from alexgreensh must be implemented clean-room. Mitigation: new modules cite README only in docstrings; code review confirms no direct translation.

---

## 8. Open questions

1. **Default embedder** — HF `bge-small-en` (64MB) vs OpenAI `text-embedding-3-small`. Default: HF for offline-first; opt-in to OpenAI via env.
2. **Reranker model** — Qwen3-reranker-0.6b (600MB) is the QMD default. Adopt or use a smaller model? Default: adopt Qwen3 if `OPEN_FANG_RERANKER=qwen3`; else skip reranking.
3. **Sandbox threshold** — 5KB (Context Mode default) or larger? Default: 5KB; monitor false-sandbox rate and adjust.
4. **Degradation-grade boundaries** — what quantile triggers S vs F? Default: σ-based calibration over first 100 runs.
5. **Validity prior shape** — beta(2,2) as chosen above; could use beta(1,1) (uniform) or beta(5,5) (stronger prior). Default: beta(2,2) — weak but non-degenerate.

---

## 9. The one-sentence v7 pitch

> OpenFang v7 cuts research-brief token cost by 50-70% end-to-end — tool outputs sandbox to FTS5 instead of flooding context, KB search becomes hybrid BM25+dense with RRF fusion, the scheduler detects and breaks retry loops, the pipeline monitors its own degradation in seven signals, repeat paper fetches return delta-only stubs, and the synthesizer ships a compact-output mode — all while every v1-v6 test stays green.

Ships as: `v6.* released → v7.0 sandbox → v7.1 hybrid search → v7.2 degradation + loop → v7.3 validity → v7.4 delta → v7.5 merkle → v7.6 compression → v7.7 release`. Test count 478 → ~560.

## 10. Strategic note

v1-v6 were about **correctness** (claim verification, failure attribution, evidence-bound synthesis). v7 is about **efficiency** — the first version where OpenFang explicitly targets token cost as a first-class metric.

For a research agent that sits in a long-running session, token efficiency compounds: every 1× reduction in per-brief tokens is a 10× reduction in weekly cost across ~50 briefs. If v7 ships the 50-70% end-to-end reduction claimed, OpenFang becomes the first research agent in the ecosystem whose operating cost is *bounded* — not by model pricing (which changes), but by the architecture's intrinsic token shape. That's a durable property.

This pairs with v5's interop theme (OpenFang speaks every ecosystem's wire format) and v6's attribution theme (OpenFang knows why it fails) to close the triangle: **OpenFang speaks, debugs, and scales**.
