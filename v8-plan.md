# OpenFang v8 — Plan

> **Prerequisite:** v7 released (v7.0 sandbox + v7.1 hybrid search shipped; v7.2–v7.7 pending). v8 is the post-v7 horizon, grounded in a new research input: **garrytan/gbrain**.

## 0. TL;DR

New research input (2026-04-22): **garrytan/gbrain** — MIT, TypeScript, 9,963★, v0.12. Same author as gstack (which shaped v4); a different project explicitly integrating with **OpenClaw** and **Hermes Agent**. GBrain's thesis is that a knowledge graph populated by **deterministic regex on every page write — zero LLM calls** beats LLM-orchestrated graph building on every axis at a fraction of the cost:

| BrainBench v1 metric | Before | After | Delta |
| --- | --- | --- | --- |
| Precision@5 | 39.2% | 44.7% | +5.4pp |
| Recall@5 | 83.1% | 94.6% | +11.5pp |
| Graph-only F1 | 57.8% | 86.6% | **+28.8pp** |
| Noise (announcement) | — | — | **−53%** |

The relevance for OpenFang is direct. v2.2 shipped a weighted citation graph with manual edge insertion; v6.3 added native arxiv BibTeX parsing. Neither does **automatic edge inference from paper body text**. GBrain proves the pattern works at near-zero marginal cost — every paper we ingest should auto-populate typed citation + technique + benchmark edges the moment it lands in the KB.

**v8 theme: Self-Wiring Knowledge Graph.**

Seven workstreams. Four are direct adoptions of GBrain patterns. Three are OpenFang-native extensions that GBrain doesn't do (because GBrain targets people/companies/meetings, we target papers/techniques/benchmarks).

| # | Workstream | Source | OpenFang gap it fills |
| --- | --- | --- | --- |
| W1 | Regex-based citation extraction on upsert | GBrain self-wire | Current `EdgeExtractor` (v6.3) only scans for arxiv ids — misses (Author, Year) style |
| W2 | Typed-edge pattern cascades | GBrain "CEO of X → works_at" | No cascade inference today |
| W3 | Backlink-boosted search ranking | GBrain backlink boost | RRF (v7.1) is rank-only; ignores graph structure |
| W4 | Stale-link reconciliation on re-upsert | GBrain reconciler | `upsert_paper` today overwrites content but leaves old edges orphaned |
| W5 | **Entity extraction beyond citations** (new) | OpenFang-native | Extract author affiliations, technique names, benchmark names as graph entities |
| W6 | **BrainBench-style eval on KB graph** (new) | OpenFang-native | Measure our Precision/Recall/F1 before + after v8; calibrate claims |
| W7 | **Remote-MCP with Bearer auth** | GBrain remote-MCP | v2.6 ships stdio only; no HTTP with auth |

---

## 1. Research refresh — GBrain

### What it is
Per-page knowledge system for AI agents. Populated from meetings, emails, Gmail, Calendar, Twilio, X. Zero-LLM ingestion via regex + pattern cascades. Backed by PGLite (embedded Postgres 17.5) with optional Supabase+pgvector. Published as a **skill pack + MCP server** — 26 skills, 30+ MCP tools, CLI with 50+ commands.

### Core architectural moves
1. **Extract on write, never on read.** Every page insert scans for named entities with pre-registered regex patterns. Links created deterministically. Read paths are pure retrieval.
2. **Typed links with inference cascades.** `works_at`, `invested_in`, `founded`, `advises`, `attended` — plus derived rules like "CEO of X" → `works_at`.
3. **Backlink boost.** Search ranks well-connected entities higher. Emergent citation-quality signal without explicit scoring.
4. **Reconcile on edit.** Page re-save re-extracts and diffs edges; stale edges expire.
5. **Dual storage**: local (PGLite) for dev; cloud (Supabase+pgvector) for deployed. Bidirectional migration.
6. **Remote MCP** with Bearer-auth over HTTP (ngrok tunnel example in docs).

### What OpenFang already has that maps
- **v2.2 weighted citation graph** — we have the edge schema (`cites | extends | refutes | shares-author | same-benchmark | same-technique-family`) but populate it mostly by hand.
- **v6.3 ArxivNativeSource** — extracts arxiv_ids from BibTeX. Narrow; doesn't capture `(Smith et al., 2023)` style inline citations.
- **v7.1 HybridSearch with RRF** — solves paraphrase-recall but ignores graph structure entirely.
- **v2.6/v5.0 MCP stdio server** — exports skills + KB + memory; no HTTP/remote yet.

### What OpenFang doesn't have that GBrain proves works
- **Zero-LLM entity extraction** on every upsert → automatic edge population.
- **Typed-edge pattern cascades** → derived edges from shallow inference rules.
- **Backlink-aware retrieval ranking** → graph structure feeds back into retrieval.
- **Reconciler** → edit-driven edge diff + expiry.
- **Remote MCP** → bearer-authenticated HTTP endpoint for cross-host ecosystem.

### What GBrain has that OpenFang should NOT adopt
- **PGLite backend swap** — SQLite+FTS5 is sufficient at our scale (< 100k papers); migration cost outweighs benefit until then.
- **People/email/calendar ingestion** — out of domain; OpenFang is paper-research-focused.
- **50+ CLI commands** — our CLI is intentionally lean (v2.0 skill list, v2.6 mcp serve/import, v3.3 trace validate). Adding 50 commands would dilute the surface.
- **Gmail/Twilio/X recipes** — not relevant to a paper-research agent.

---

## 2. Goals and Non-Goals

### Goals
1. **Zero-LLM edge inference** on every `upsert_paper` — auto-populate typed edges from paper content.
2. **Pattern-cascade derivation** — one level deep (A cites B + B extends C → A depends_on C weak edge).
3. **Backlink boost in HybridSearch** — well-cited papers rank higher, all else equal.
4. **Reconciler on re-upsert** — stale edges removed; new edges added; provenance preserved.
5. **Entity expansion beyond papers** — authors (exist), **affiliations** (new), **techniques** (new), **benchmarks** (new), each a first-class graph entity.
6. **BrainBench-analog eval** — curated 20-paper graph corpus; measure Precision@5 / Recall@5 / Graph-F1 pre-v8 and post-v8.
7. **Remote MCP endpoint** — Bearer-authenticated HTTP surface exposing the 7 read-only tools we ship in v2.6+v5.0.

### Non-Goals
- **No PGLite or Postgres** — SQLite+FTS5 remains the backend.
- **No people/meetings/email ingestion** — out of domain.
- **No 50-command CLI expansion** — hold the current lean surface.
- **No cloud-sync dual-storage** — local-first stays the model; deployment variants are a user concern.
- **No TypeScript rewrite** — Python.
- **No noise reduction claim we can't verify** — we measure our own BrainBench-analog and publish; we do NOT quote GBrain's −53% as our target.

---

## 3. Workstreams

### W1 — Zero-LLM Citation + Entity Extraction on Upsert

**Source.** GBrain's self-wiring mechanism — every page write runs regex patterns on the markdown and emits typed edges.

**Why v8.** v6.3's EdgeExtractor only captures bare arxiv_ids. Real paper abstracts reference work as `(Smith et al., 2023)`, `[1]` with a references list, `per Wang & Li (2022)`. GBrain's pattern shows these are deterministically extractable without LLM cost.

**Design.**
- New `src/open_fang/kb/self_wire.py` with:
  - `PatternRegistry` — ordered list of `(pattern_name, regex, edge_kind, extractor_fn)` tuples.
  - `_extractors`: arxiv-id, `(Author, Year)` inline citation, `[N]` bracketed reference number with references-section resolver, technique-name (e.g., "ReWOO", "ReAct", "Chain-of-Thought" — seeded list + pluralizable forms), benchmark-name (`SWE-bench`, `BFCL`, `τ²-Bench`, etc.).
  - `SelfWirer(kb).process(paper_id, content)` → list of `InferredEdge(src_id, dst_id, kind, pattern_name, span)`.
  - Hooks into `KBStore.upsert_paper()` as a post-insert callback.
- Edge-kind mapping: arxiv id → `cites`; inline cite → `cites` (weak confidence if author-only match); technique overlap → `shares-technique`; benchmark overlap → `same-benchmark`.
- Confidence score per inferred edge; `edges` table gets `confidence REAL` column.

**Tests** (target +12)
- Pattern-by-pattern unit tests.
- Integration: seed 5 papers with known cross-references, run self-wire, verify edge count + kinds.
- Back-compat: all v2.2/v6.3 edge tests still pass.

### W2 — Typed-Edge Pattern Cascades (depth-1)

**Source.** GBrain's "CEO of X → works_at(CEO, X)" inference.

**Why v8.** Cascades turn sparse citation graphs into dense typed-edge graphs without additional ingestion.

**Design.**
- New `src/open_fang/kb/cascades.py` with 4 rules:
  - `A cites B ∧ B extends C ⇒ A depends_on C` (weak, confidence 0.4).
  - `A cites B ∧ A cites C ⇒ B co_cited_with C` (weak, confidence 0.5).
  - `A shares-author-with B ∧ B extends C ⇒ A likely-related-to C` (weak, confidence 0.3).
  - `A same-benchmark-as B ∧ B same-benchmark-as C ⇒ A same-benchmark-as C` (transitive, confidence 0.6).
- Cascade runs after W1 self-wiring; depth-1 only (no recursive explosion).
- Cascade-inferred edges get `provenance='cascade:<rule_name>'` in the `edges` table.

**Tests** (target +8)
- Each rule has an isolated unit test with a 3-paper seed.
- Combined test: 10 papers, verify cascade output bounded.

### W3 — Backlink-Boosted Search Ranking

**Source.** GBrain's "backlinks boost search ranking" pattern.

**Why v8.** v7.1's RRF fuses BM25 and dense; v8 fuses a third signal — how many papers in the KB cite this one. Well-cited papers rank higher for ambiguous queries.

**Design.**
- `HybridSearch` grows an optional third rank list: **backlink rank** (`ORDER BY backlink_count DESC`).
- RRF combines three rank lists with the same k=60 weighting.
- Opt-in via `HybridSearch(..., include_backlinks=True)`; default off until W6 eval shows it helps.

**Tests** (target +6)
- Unit: backlink count retrieved correctly from `edges` table.
- Unit: RRF with 3 lists behaves analogous to 2-list case.
- Eval: paraphrase-query recall with backlinks on vs off — must not regress.

### W4 — Stale-Link Reconciliation on Re-Upsert

**Source.** GBrain reconciler — "stale links are reconciled when pages are edited."

**Why v8.** Today, `upsert_paper` replaces content but leaves old auto-wired edges in place. If a v1 abstract cited arxiv:123 and v2 doesn't, the edge persists forever.

**Design.**
- `KBStore.upsert_paper()` invokes a reconciliation pass:
  1. Compute new self-wired edges via W1 on the new content.
  2. Compute old self-wired edges attributed to this paper (filter by `provenance='self-wire:*'`).
  3. Diff: delete edges present in old but missing in new; insert edges present in new but missing in old.
  4. Manually inserted edges (no `self-wire:` provenance) are preserved.
- Add `provenance TEXT` to the `edges` table.

**Tests** (target +5)
- Upsert v1 content → 3 edges. Upsert v2 content with 2 overlapping + 1 new → 3 edges, one deleted, one added.
- Manually inserted edge survives re-upsert.
- Reconciliation is idempotent.

### W5 — Entity Expansion: Authors + Affiliations + Techniques + Benchmarks

**Why v8.** Papers reference more than other papers. Authors have affiliations that change; techniques are reused across papers; benchmarks get rerun. GBrain's "people/companies/concepts" translates to "authors/affiliations/techniques/benchmarks" in our domain.

**Design.**
- Schema: 4 new tables — `authors`, `affiliations`, `techniques`, `benchmarks`. Each has `id`, `name`, `canonical_name`, `first_seen_at`, `mention_count`.
- W1's pattern registry extended with extractors for each entity type.
- New edge kinds (additions to existing enum): `authored_by`, `affiliated_with`, `uses_technique`, `evaluates_on`.
- Entity extraction is zero-LLM (regex + seeded name lists; grow the lists over time via the self-research loop in v6.5).

**Tests** (target +10)
- Each entity type gets a unit test on extraction.
- Integration: 5-paper seed → populated entity tables + typed edges.
- Deduplication: same author under two spellings collapsed via canonical-name heuristic.

### W6 — BrainBench-Analog Eval

**Why v8.** We need our own metrics to back v8 claims. GBrain published 240 pages + Precision/Recall/F1. We build a similar curated graph corpus and measure before/after.

**Design.**
- New `tests/fixtures/graph_corpus.py` — 20 papers, hand-annotated with ground-truth edges (20-40 typed edges across the set), 20 hand-authored "graph queries" (e.g., "papers that extend ReAct").
- New `src/open_fang/eval/graph_metrics.py`:
  - `precision_at_k(retrieved, relevant, k=5)`.
  - `recall_at_k(retrieved, relevant, k=5)`.
  - `graph_f1(retrieved_edges, ground_truth_edges)`.
- Evaluation test `tests/evaluation/test_graph_bench.py` — asserts v8 doesn't regress on these numbers.

**Tests** (target +8)
- Each metric has a unit test.
- Evaluation: v8-enabled config vs v7 baseline; record numbers.

### W7 — Remote MCP with Bearer Auth

**Source.** GBrain docs ship a remote-MCP example with Bearer auth over HTTP.

**Why v8.** Our stdio MCP (v2.6+v5.0) works for Claude Code / Cursor / Codex local installs but not for multi-user / remote-host scenarios. GBrain's pattern is minimal: same JSON-RPC, over HTTP, with a single Bearer header.

**Design.**
- `src/open_fang/mcp_server/http.py` — FastAPI-mounted `POST /mcp/rpc` endpoint that accepts the same JSON-RPC payload our stdio server handles.
- Bearer token via `OPEN_FANG_MCP_TOKEN` env var; missing/wrong token → 401.
- Opt-in: only mounts when `OPEN_FANG_MCP_HTTP=1` is set.
- Rate limiting: token-bucket per-IP, 100 req/min default (sliding window).

**Tests** (target +6)
- Unit: POST /mcp/rpc with valid token → same response as stdio handler.
- Unit: wrong token → 401.
- Unit: missing token → 401.
- Unit: rate limit triggers 429.
- Integration: round-trip `initialize → tools/list → tools/call` over HTTP.

---

## 4. Cross-cutting concerns

### CC-1 — Edge provenance is load-bearing (extends v4.4 attribution discipline)
Every row in `edges` carries `provenance TEXT` labeling the mechanism (`self-wire:arxiv-id`, `cascade:transitive-benchmark`, `manual`, `native-arxiv-bibtex`, etc.). The W4 reconciler reads this to decide what it can delete. v8 is the breaking change on `edges` schema.

### CC-2 — No LLM in the ingestion path
The whole v8 thesis: extraction is zero-LLM. LLMs are expensive, stochastic, and we already have a 5-tier verifier downstream. Pattern registries grow manually + via v6.5 self-research; the ingestion path stays deterministic.

### CC-3 — Preserve manual-edge safety
Edges without `self-wire:*` provenance are never touched by the reconciler. Users who hand-curate important edges trust the system not to erase their work.

### CC-4 — Release cadence check
Weekly: feed cron + eval re-run. Bi-weekly: evolving arena. Monthly: degradation-monitor review. **Quarterly: BrainBench-analog re-run (W6) with published numbers** (new).

---

## 5. Phases

| Phase | Scope | Exit | Tests target |
| --- | --- | --- | --- |
| v7.* (prereq) | v7.2 – v7.7 green | v7 released | ~560 |
| v8.0 | W1 self-wire (citations + techniques + benchmarks) | 12 tests green; 5-paper seed yields expected auto-edges | ~575 |
| v8.1 | W2 cascade rules | each of 4 rules green; 10-paper integration bounded | ~585 |
| v8.2 | W5 entity expansion (authors/affiliations/techniques/benchmarks) | 4 new tables populated + entity-edge tests green | ~600 |
| v8.3 | W4 reconciliation on re-upsert | edge diff idempotent + manual-edge survival | ~610 |
| v8.4 | W3 backlink-boosted HybridSearch (3-list RRF) | no regression + measurable boost on W6 corpus | ~620 |
| v8.5 | W6 BrainBench-analog eval + publish baseline | Precision@5 ≥ current; Recall@5 ≥ current; Graph-F1 measured | ~635 |
| v8.6 | W7 remote MCP + Bearer auth | HTTP round-trip + 401/429 tests green | ~645 |
| v8.7 | Release v8 | docs + dogfood + cadence review | ~645 |

Target: 560 (v7.7) → ~645 by v8.7. +85 tests across 7 workstreams.

---

## 6. Trade-offs

| Technique | Source | Workstream | Chosen |
| --- | --- | --- | --- |
| Regex-based entity extraction (zero LLM) | GBrain | W1 | ✅ |
| Typed-edge pattern cascades (depth-1) | GBrain | W2 | ✅ |
| Backlink-boosted search ranking | GBrain | W3 | ✅ opt-in |
| Stale-link reconciliation on re-upsert | GBrain | W4 | ✅ |
| Entity expansion beyond citations | OpenFang-native | W5 | ✅ |
| BrainBench-analog graph eval | OpenFang-native | W6 | ✅ |
| Remote MCP with Bearer auth | GBrain | W7 | ✅ opt-in |
| PGLite / Postgres backend | GBrain | — | ❌ SQLite at our scale |
| pgvector for embeddings | GBrain | — | ❌ v7.1 HashEmbedder + optional HF cover it |
| Gmail / Calendar / Twilio / X ingestion | GBrain | — | ❌ out of domain |
| People / companies / meetings entities | GBrain | — | ❌ domain swap |
| 50+ CLI commands | GBrain | — | ❌ lean surface |
| Cloud-sync dual-storage | GBrain | — | ❌ local-first |
| Recursive cascade (depth > 1) | hypothetical | W2 | ❌ edge explosion |
| LLM-based entity extraction | alternate design | W1 | ❌ contradicts CC-2 |

---

## 7. Risks

- **Regex false-positives.** "(Smith et al., 2023)" could match a non-existent paper. Mitigation: W1 only emits edges pointing to papers **already in the KB**; unmatchable references become `mention` rows (no edge), surfaced for manual curation.
- **Cascade edge explosion at scale.** 10,000 papers × depth-1 cascades × 4 rules ≈ 40,000 inferred edges. Mitigation: cascade runs only on high-confidence base edges (`self-wire:arxiv-id`); weak-confidence edges don't cascade.
- **Reconciler deletes edges the user curated manually.** Catastrophic data loss. Mitigation: W4 is strictly scoped by `provenance LIKE 'self-wire:%'`; manual edges are untouchable.
- **Backlink gaming.** An adversarial paper upsert with 100 fake citations inflates its backlink count. Mitigation: backlink count computed only from verified-provenance edges; v2.5 security probes already guard KB promotion.
- **BrainBench-analog corpus is too small.** 20 papers is below GBrain's 240. Mitigation: v8 eval is baseline-establishing, not absolute; we publish our own numbers on our own corpus; v9 expands.
- **Remote MCP token leak.** Bearer tokens in logs, env vars. Mitigation: token validation never logs the token; 401 responses never echo the sent value; rotation docs shipped with the feature.

---

## 8. Open questions

1. **Pattern registry bootstrap** — how many technique names and benchmark names do we seed? Default: a hand-curated list of ~50 techniques and ~30 benchmarks from the v7-era KB; grow via v6.5 self-research.
2. **Cascade confidence thresholds** — depth-1 cascades with base confidence > 0.6? Or > 0.8? Default: > 0.6 (inclusive). Tighten if spurious edges dominate.
3. **Entity canonicalization** — "R. Smith", "Robert Smith", "R Smith" as one author? Default: name-token-set canonicalization + year-within-5 overlap; flag ambiguous for human review.
4. **W7 rate-limit model** — per-IP token bucket or per-token? Default: per-token (Bearer) to avoid shared-NAT punishment.
5. **Schema migration for provenance column** — add via `ALTER TABLE` with `IF NOT EXISTS` guard? PostgreSQL-compatible path? Default: SQLite-only; add on next open.

---

## 9. The one-sentence v8 pitch

> OpenFang v8 makes the knowledge graph **self-wiring**: every paper ingested auto-populates typed citation, technique, benchmark, and authorship edges via deterministic zero-LLM regex extraction, depth-1 pattern cascades fill sparse regions, stale links expire on re-upsert, backlink counts boost HybridSearch ranking, and a Bearer-authenticated remote-MCP endpoint exposes the graph to the rest of the agent ecosystem — calibrated against our own BrainBench-analog corpus.

Ships as: `v7.* green → v8.0 self-wire → v8.1 cascades → v8.2 entities → v8.3 reconciler → v8.4 backlink-boosted search → v8.5 graph eval → v8.6 remote MCP → v8.7 release`. Test count 560 → ~645.

## 10. Strategic note

The v5/v6/v7 triangle (**speaks / debugs / scales**) gets a fourth corner with v8: **wires**.

> OpenFang v8 wires its own knowledge graph automatically, at zero LLM cost, with a calibrated eval that lets us say how much better — not just "better".

The GBrain insight — that regex + pattern cascades on ingestion beats LLM orchestration on read — is orthogonal to everything v1–v7 absorbed. v7 made us token-lean; v8 makes us graph-dense. Together they compound: a denser graph cuts query tokens further (more precise retrieval) and a leaner context lets us put more graph structure into context per brief.

And GBrain's +28.8pp Graph-F1 is a number we can honestly aspire to — but only by running our own BrainBench-analog (W6) before claiming parity. v8 publishes our measurements, whatever they are.
