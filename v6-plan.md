# OpenFang v6 — Plan

> **Prerequisite:** v5 released (425 tests). All 10 research sources from the prior rounds absorbed. v6 is the **post-interop horizon**: what's next after we talk to every tool in the ecosystem?

## 0. TL;DR

v5 was **ecosystem interop**: claude-mem parity, Hermes-Atropos pipeline, multica runtime adapter, agentskills.io compliance, gstack 3-mode verification. v6 is **"know why it fails"** — closing the loop that v2.1 EvolvingArena opened.

Deep-research pass over our 67-file local corpus (run 2026-04-22) surfaced a pattern we've been implicitly pointing at across the entire project but never materialized: **primitive-level failure attribution**. Every piece of OpenFang's self-improvement machinery — TrajectoryExtractor (v2.1), Diagnostician (v2.1), EvolvingArena (v2.1), chaos hooks (v2.5), trajectory export (v3.3), skill-tree navigation (v5.1) — silently assumes it can *locate* the failing primitive. None of them actually can. Every failure today is a leaf-level "claim X didn't verify" or "node Y crashed"; we can't cheaply ask "which primitive in the harness degraded?"

The corpus's recommended breakthrough project — [docs/67-recommended-breakthrough-project.md](../../docs/67-recommended-breakthrough-project.md) — is Gnomon: a Harness-IR + Harness-Aware Failure Classifier + Stochastic Harness Perturbation stack. v1 flagged this as "telemetry floor" and shipped only the spans; v6 builds the classifier.

Plus four concrete, smaller wins surfaced by the same research pass:

- **ReBalance confidence-steered reasoning** — training-free, direct token savings. Easy win.
- **Lightweight symbolic claim-number verifier** — catches "claimed 5×, actual 3×" class of fabrications our current tiers miss.
- **Native arxiv/GitHub/HuggingFace integrations** — Rosalind-lite specialization; we currently rely on generic HTTP clients.
- **Chaos → HAFC feedback loop** — pair existing v2.5 chaos hooks with v6 attribution to auto-discover fragile primitives.

Plus one recursive insight: **OpenFang is uniquely positioned to research itself**. W6 uses OpenFang to plan v7.

---

## 1. Research refresh — what's new since v5

### 1.1 Corpus mining (local docs)

| Doc | Pattern | Under-exploited? |
| --- | --- | --- |
| [32-recurrent-depth](../../docs/32-recurrent-depth-implicit-reasoning.md) | Iterated layers for deep reasoning without extra tokens | Partial — defer to v7 when open models grow |
| [37-neuro-symbolic](../../docs/37-neuro-symbolic-ai.md) | SAT/SMT + LLM hybrid; symbolic verification | **Yes — lightweight version for W3** |
| [45-hyperagents](../../docs/45-hyperagents-self-modification.md) | Meta-meta-loops | No — too risky, defer past v6 |
| [50-metcl](../../docs/50-metcl-metaphor-reasoning.md) | Typicality-based metaphor reasoning | No — 3/5 relevance, marginal ROI |
| [51-rebalance](../../docs/51-rebalance-efficient-reasoning.md) | Training-free confidence-guided steering | **Yes — W2** |
| [67-breakthrough](../../docs/67-recommended-breakthrough-project.md) | Gnomon: HIR + HAFC + SHP | **Yes — W1, the centerpiece** |
| [28/30/33/39/48](../../docs) domain specialists | Rosalind-style native DB integrations + safety gating | **Yes — W4 (lite)** |

### 1.2 Awesome-list refresh

Fresh 2026 entries checked; three are directly relevant to v6:

- **ClawBench (2604.08523)** — submission-interception browser-agent eval. OpenFang's domain is text, so defer, but the "intercept the write path to eval without side effects" pattern applies to our KB promotion gate. Take note.
- **Beyond Offline A/B Testing (2604.09549)** — agent simulation for eval. Fits v6 W6 (self-research).
- Remaining entries either absorbed in v5 or out of scope.

### 1.3 Net-new insight — recursion

OpenFang's unique position: it's a research agent for *research-agent research*. No other tool in the ecosystem has this property. v6 W6 formalizes the recursion: run OpenFang on every v1–v5 dogfood brief and use the outputs to auto-propose v7 workstreams. Publishing agents don't research; research agents on narrow domains can but don't self-apply. We can.

---

## 2. Goals and Non-Goals

### Goals
1. Ship a primitive-level **failure-attribution classifier** (HAFC-lite) so every pipeline failure resolves to one of ≤ 15 named primitives.
2. Wire an **automatic ReBalance-style halt** into the verifier loop using existing LLM confidence signals — target 20% token reduction on repeat queries.
3. Add a **symbolic claim-number verifier tier** between Tier-4 executable and Tier-5 critic.
4. Deepen integration with **arxiv API (BibTeX)**, **GitHub (code-for-paper)**, and **HuggingFace (model lineage)** — native adapters replace the current generic HTTP source-router paths.
5. Pair **v2.5 chaos hooks** with **v6 HAFC** so each chaos round produces an attribution report: which primitive degraded under which perturbation.
6. Run **OpenFang on itself** — weekly self-research brief that proposes v7 workstreams.

### Non-Goals
- **No full Gnomon** — that's a dedicated sibling project per [docs/67](../../docs/67-recommended-breakthrough-project.md). v6 ships *HAFC-lite*: 12 primitives max, attribution via rules + one LLM call per failure (no trained classifier).
- **No hyperagents** — meta-meta-loops flagged as pre-production across multiple corpus entries.
- **No domain post-training** — generalist + tools is winning strategy per v4/v5 learnings. We add tools, not new weights.
- **No METCL / metaphor-reasoning layer** — low ROI.
- **No browser agent (ClawBench pattern)** — text/arxiv stays the substrate.
- **No Rust/Go rewrites** — Python stability.

---

## 3. Workstreams

### W1 — HAFC-lite: primitive-level failure attribution

**Source.** [docs/67-recommended-breakthrough-project.md](../../docs/67-recommended-breakthrough-project.md) Gnomon project.

**Why v6.** Every self-improvement loop we built (v2.1 EvolvingArena, v2.2 graph-walk synthesis, v4.3 isolated supervisor) silently assumes failure-locality. Without it, Autogenesis patches are coarse — "pipeline faithfulness dropped from 0.95 to 0.87" doesn't tell the diagnostician which primitive broke. HAFC-lite is the smallest version that unblocks the rest.

**Design.**

- New module `src/open_fang/attribution/` with:
  - `primitives.py` — canonical 12-primitive enum (planner / scheduler-dispatch / source-router / kb-lookup / synthesis / mutation-probe / llm-judge / executable-verifier / critic / memory-compact / skill-activation / permission-gate).
  - `classifier.py` — rules-first attribution over a `PipelineResult`:
    - Rule 1: failed_node exists → attribute to `source-router` or `kb-lookup` depending on kind.
    - Rule 2: faithfulness < 0.9 + mutation_warnings > 0 → attribute to `mutation-probe`.
    - Rule 3: faithfulness < 0.9 + executable_failures > 0 → attribute to `executable-verifier`.
    - Rule 4: faithfulness < 0.9 + claim missing evidence_ids → attribute to `synthesis`.
    - Rule 5: … (9 more rules for remaining primitives).
    - Fallback: optional LLM-based attribution when rules don't fire, using span data as input.
  - `report.py` — emits an `AttributionReport` per failed run: one `(primitive, evidence_span, confidence)` tuple per failure.

- Integration: `OpenFangPipeline.run()` appends an `AttributionReport` to `PipelineResult` when `report.faithfulness_ratio < 0.9` or any failed nodes.

- Endpoint: `GET /v1/attribution/recent?limit=50` — returns the attribution reports from the most recent runs (pulled from memory store's observations).

**Tests.** (target +20)
- Unit: each of 12 primitives has at least one rule that attributes to it; fallback invoked when no rule matches.
- Unit: classifier stays silent on clean runs.
- Integration: seed pipeline with a known failure (e.g., fabricated citation) → attribution reports `synthesis` primitive with evidence.
- Integration: seed pipeline with a mutation-corpus fabrication → attribution reports `mutation-probe` primitive.

### W2 — ReBalance-style confidence-steered halt

**Source.** [docs/51-rebalance-efficient-reasoning.md](../../docs/51-rebalance-efficient-reasoning.md).

**Why v6.** Research agents often re-analyze the same paper across multiple specialists, generating redundant reasoning. A confidence signal from the primary LLM lets us early-halt when the pipeline's outputs converge.

**Design.**

- New `verify/halt.py` with:
  - `ConfidenceMonitor` — tracks last N judge verdicts' variance + LLM self-reported confidence (Anthropic's extended-thinking model returns a confidence metadata field).
  - Halt signal: `should_halt(window, threshold=0.85)` → True when the last 3 judge verdicts all report ≥ threshold confidence AND have the same `supported` verdict.
  - Triggered at **synthesis → verifier → critic** boundary: if the synthesizer's output has already passed 3 verifier tiers with high confidence, skip critic + cross-model.

- Pipeline wiring: `OpenFangPipeline(halt_monitor=ConfidenceMonitor())` — opt-in. Default off.

**Tests.** (target +8)
- Unit: 3 high-confidence verdicts → halt signal.
- Unit: 3 mixed-confidence verdicts → no halt.
- Unit: single high-confidence verdict → no halt (needs window).
- Integration: pipeline with halt + high-confidence scripted LLM → skips critic tier (measured via span count).
- Evaluation: 10-brief sweep with halt on vs off → ≥ 20% span-count reduction, no faithfulness regression.

### W3 — Symbolic claim-number verifier (Tier 4.5)

**Source.** [docs/37-neuro-symbolic-ai.md](../../docs/37-neuro-symbolic-ai.md), lightweight adaptation.

**Why v6.** Our Tier-4 executable verifier catches claims whose *full assertion* fails, but claims like "X is 5× faster than Y" that should be cross-checkable against structured numbers (`structured_data`) often slip through because the claim text parses but the number doesn't match. A small symbolic layer bridges the gap.

**Design.**

- New `verify/symbolic.py` with:
  - `extract_numeric_assertions(claim_text)` — regex-based extraction of `<N><unit_or_multiplier>` patterns + comparison operators. Returns e.g., `[NumericAssertion(value=5, multiplier='x', relation='faster_than', subject='X', object='Y')]`.
  - `SymbolicVerifier` — for each assertion, query `structured_data` across cited evidence for matching keys (e.g., `x_speed`, `y_speed`); compute the observed ratio; compare against assertion within ±15% tolerance.
  - Emits `SymbolicVerdict(passed, observed_ratio, claimed_ratio, reason)`.

- Integration: new tier between existing Tier-4 (executable) and Tier-5 (critic). Runs only on `quantitative` claim-kind per v4.1 router. Rejection downgrades the claim.

**Tests.** (target +10)
- Unit: regex extraction on a range of numeric claims.
- Unit: verdict on matching vs mismatching ratios.
- Unit: silent on non-quantitative claims.
- Integration: mutation corpus — the "tenfold" fabrication passes Tier-2 mutation but fails Tier 4.5 symbolic because 120/600 ≠ 10.
- Evaluation: mutation-resistance floor (≥0.85) holds with the new tier enabled.

### W4 — Native arxiv/GitHub/HuggingFace integrations

**Source.** [docs/30-gpt-rosalind-domain-specialized.md](../../docs/30-gpt-rosalind-domain-specialized.md).

**Why v6.** v1.2 shipped generic HTTP-based `ArxivSource` / `S2Source` / `GithubSource`. That works but under-exploits each service's specialized endpoints: arxiv exposes BibTeX + reference-list APIs; GitHub has code-for-paper metadata (via Papers With Code linkage); HuggingFace publishes model lineage graphs. Native adapters let us build richer citation edges.

**Design.**

- `src/open_fang/sources/arxiv_native.py` — extends existing ArxivSource with:
  - `fetch_bibtex(arxiv_id)` — retrieves BibTeX; parses into reference graph.
  - `fetch_references(arxiv_id)` — uses arxiv's bibliography endpoint when available.
- `src/open_fang/sources/github_native.py` — extends GithubSource with:
  - `find_code_for_paper(arxiv_id)` — looks for Papers With Code linkage; falls back to keyword search.
  - `fetch_repo_readme(url)` — fetches README as auxiliary evidence.
- `src/open_fang/sources/huggingface.py` (new) — `HFSource`:
  - `find_model_by_paper(arxiv_id)` — HF's model hub linkage.
  - `fetch_model_card(model_id)` — extracts stated capabilities + eval numbers.
- Each adapter updates the KB promotion path to add typed edges (`cites`, `has_code`, `has_model`).

**Tests.** (target +12)
- Unit: each adapter with mocked httpx responses.
- Integration: seed KB with an arxiv paper → native arxiv adapter adds `cites` edges to known KB papers.
- Integration: paper-with-code roundtrip produces `has_code` edges.

### W5 — Chaos × HAFC closed loop

**Why v6.** v2.5 chaos hooks inject faults; v6 HAFC attributes failures. Pairing them auto-discovers which primitives are fragile under which perturbations.

**Design.**

- New `scripts/chaos_scan.py` — invokes the pipeline N times against a fixed brief, each run with a different chaos-mode config (`network_drop:0.3`, `memory_drop:0.2`, etc). Collects attribution reports, groups by `(chaos_mode, primitive)`, emits a fragility matrix.
- CLI: `openfang chaos scan --brief "rewoo vs react" --rounds 20` — emits the matrix as JSON/markdown.
- v6 ships the scanner; v7 ships the response (auto-generated hardening patches).

**Tests.** (target +5)
- Unit: scanner aggregates attributions across rounds.
- Integration: 10-round scan with `network_drop:1.0` attributes every failure to `source-router`.

### W6 — OpenFang researches itself (recursion unlock)

**Why v6.** Unique to this project: we're a research agent whose narrow domain includes research-agent research. v6 formalizes the self-research loop.

**Design.**

- `scripts/self_research.py` — given a version-plan file (v1 through v5), the script extracts each plan's "open questions" section, converts each to a `Brief`, runs OpenFang through all briefs, and emits a consolidated "v7 workstream candidates" report.
- CLI: `openfang self-research --plan v5-plan.md --out v6-dogfood-report.md`.
- Cron: opt-in, quarterly default (matches v5.4 feed cron cadence).

**Tests.** (target +5)
- Unit: open-questions extractor on each of v1–v5 plan files; each returns ≥ 1 question.
- Integration: one full `openfang self-research` cycle produces a report; report is parseable.

---

## 4. Cross-cutting concerns

### CC-1 — Release cadence (carry-over from v5 CC-1)
Weekly: feed cron (W6). Bi-weekly: evolving arena. Monthly: docs refresh. Quarterly: self-research round + new-version plan.

### CC-2 — Attribution vocabulary is load-bearing
The 12-primitive enum in W1 becomes the shared vocabulary for Autogenesis patches (future v7+). Changing this enum is a breaking change; version it.

### CC-3 — No Gnomon
v6 ships HAFC-lite, not full Gnomon. Gnomon remains a sibling project per the corpus's recommendation.

### CC-4 — v6 is the last pre-scaling version
v1–v5 were all "single user, single session". v7 is expected to be where we tackle multi-tenant + scaling. v6 is last chance to solidify single-user behavior before that complexity lands.

---

## 5. Phases

| Phase | Scope | Exit criteria | Tests target |
| --- | --- | --- | --- |
| v6.0 | W1 HAFC-lite (12 primitives + rules-first classifier) | seeded-failure tests attribute to expected primitive | ~445 |
| v6.1 | W2 ReBalance confidence halt | 20% span-count reduction on 10-brief sweep | ~455 |
| v6.2 | W3 symbolic claim-number verifier | mutation corpus: tenfold fabrication caught by Tier 4.5 | ~465 |
| v6.3 | W4 native arxiv/GitHub/HF adapters | BibTeX round-trip + Papers-With-Code linkage | ~480 |
| v6.4 | W5 chaos × HAFC scanner | fragility matrix green on 3 chaos configs | ~485 |
| v6.5 | W6 self-research script | one quarterly cycle produces v7 candidates | ~490 |
| v6.6 | Release v6 | docs + dogfood + cadence review | ~490 |

Target: 425 (v5.6) → ~490 by v6.6. +65 tests, roughly one half-day per phase at current velocity.

---

## 6. Trade-offs

| Technique | Source | Workstream | Chosen |
| --- | --- | --- | --- |
| HAFC-lite (rules + fallback LLM attribution) | docs/67 | W1 | ✅ |
| ReBalance confidence-guided halt | docs/51 | W2 | ✅ |
| Symbolic claim-number verifier (Tier 4.5) | docs/37 | W3 | ✅ |
| Native arxiv/GitHub/HF adapters | docs/30 Rosalind-lite | W4 | ✅ |
| Chaos × HAFC fragility matrix | docs/67 SHP + v2.5 | W5 | ✅ |
| OpenFang self-research loop | unique | W6 | ✅ |
| Full Gnomon HIR + trained HAFC | docs/67 | — | ⏸ sibling project |
| Domain post-training | docs/28/30/33 | — | ❌ generalist + tools wins |
| Hyperagents meta-meta-loops | docs/45 | — | ❌ pre-production |
| METCL metaphor reasoning | docs/50 | — | ❌ low ROI |
| Browser agent (ClawBench shape) | 2604.08523 | — | ❌ out of domain |
| Recurrent-depth model runtime | docs/32 | — | ⏸ v7+ (needs open models) |

---

## 7. Risks

- **HAFC-lite becomes a scapegoat.** A rules-based classifier will mis-attribute subtle failures, and users might trust it too much. Mitigation: every attribution carries a `confidence` field + "evidence span" for the user to audit. Low-confidence attributions explicitly say "multiple primitives possible".
- **ReBalance halt regresses faithfulness on hard briefs.** High-confidence early verdicts might be wrong on ambiguous claims. Mitigation: halt is opt-in + only skips critic/cross-model, never Tier 1-3. Tier 1-3 always run.
- **Native adapters become fragile.** arXiv/GitHub/HF APIs evolve. Mitigation: adapters are thin wrappers; fallback to the v1.2 generic HTTP paths if a native endpoint 404s.
- **Self-research recursion produces garbage.** If OpenFang's output on "how to improve OpenFang" is bad, the v7 plan inherits the badness. Mitigation: human gate — self-research outputs are *candidates*, not auto-adopted workstreams.
- **Chaos × HAFC infinite loop.** Scanner running in a loop against a live-reload instance could thrash. Mitigation: scanner is CLI-invoked (manual or cron-scheduled), never automatic on every run.

---

## 8. Open questions

1. **HAFC classifier: 12 primitives, or finer?** Start with 12; if attribution is ambiguous on >15% of failures, split into 15-18. Monitor.
2. **Confidence signal source in W2.** Anthropic's extended-thinking exposes metadata; OpenAI doesn't (yet). Dual-path: use confidence when available, fall back to verdict-window variance when not.
3. **W3 tolerance in symbolic verifier.** Default ±15%; tighten to ±5% on explicit-numbers claims, loosen to ±25% on qualitative ratios.
4. **W4 rate-limiting.** Native adapters talk to external APIs. GitHub + HF have stricter limits than arxiv. Per-adapter token bucket in the source-router.
5. **W6 cadence.** Quarterly default matches v5.4 feed cron. Monthly may be better for a live project; revisit after first cycle.

---

## 9. The one-sentence v6 pitch

> OpenFang v6 closes the **primitive-level failure-attribution loop** that every self-improvement mechanism in v1–v5 silently assumed — ships HAFC-lite, pairs it with chaos-scan to auto-map fragility, adds a symbolic tier that catches claim-number mismatches, deepens native arXiv/GitHub/HF integration, and starts the recursive self-research loop that eventually plans v7 without us.

Ships as: `v5.* released → v6.0 HAFC-lite → v6.1 confidence halt → v6.2 symbolic verifier → v6.3 native adapters → v6.4 chaos scanner → v6.5 self-research → v6.6 release`. Test count 425 → ~490.

## 10. One strategic note

The **recursion in W6 is unique to OpenFang**. No other tool in the ecosystem we've surveyed (claude-mem, multica, Hermes, gstack, ECC, Corpus2Skill, CORAL) has the property that it can research its own research literature. We're uniquely positioned because our narrow domain *is* research-agent research.

If v7 ships a v7 plan that wasn't written by a human — auto-generated by the v6 self-research loop — that's a genuinely new capability in the ecosystem, not just another interop point. The v5 interop work was table stakes; W6 is where OpenFang becomes *different*.
