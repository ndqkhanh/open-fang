# OpenFang v4 — Plan

> **Prerequisite:** v2 complete (we're at 262 tests, v2.7 release doc still pending) and **v3 shipped** per [v3-plan.md](v3-plan.md). v4 is the post-v3 horizon — what a "next-next version" looks like once agentskills.io alignment, progressive-disclosure memory, supervisor+subagents, and trajectory export are all live.

## 0. TL;DR

One new research input shifted the horizon: **`garrytan/gstack`** (79.4k★, MIT, TypeScript 74%). It is a production-validated specialist-role library — **23 Claude Code skills** shaped as roles (CEO, designer, engineer manager, QA lead, security officer, release engineer), with **Conductor** orchestrating 10–15 isolated Claude Code sessions in parallel, plus **cross-model verification** (`/review` Claude + `/codex` OpenAI) for independent second opinions.

Three things this changes:

1. **Role specialization scales.** v3.2 proposes 5 specialists (Survey/DeepRead/ClaimVerifier/Synthesis/Critic). gstack's 23-role cohort at 79k stars says "go further" — research-agent roles like ResearchDirector, Methodologist, ThreatModeler, Publisher are absent from our plan and each adds measurable value.
2. **Cross-model verification beats same-model-twice.** Our Tier 3 LLM judge + CriticAgent both use the same model family. gstack proves that routing to a different family (Claude ↔ OpenAI) catches a different failure class. Upgrading the verifier to cross-family for high-risk claims is worth a tier.
3. **Conductor isolated-session parallelism** is a real alternative to v3.2's asyncio coordination. Isolated sessions mean each specialist has its *own* context, eliminating cross-contamination on long research runs at the cost of a subprocess per specialist.

Everything else from v3-plan.md still stands. v4 is additive, not a rewrite.

---

## 1. Research refresh — what changed since v3-plan.md

| Source | v3 status | v4 delta |
| --- | --- | --- |
| affaan-m/everything-claude-code | adopted format | no change |
| arxiv:2604.05013 (Atomic Skills) | mutation + atomic taxonomy adopted | no change |
| arxiv:2604.18292 (Agent-World) | arena loop + graph-walk synthesis adopted | no change |
| VoltAgent/awesome-ai-agent-papers | rolling feed | no change |
| nousresearch/hermes-agent | W1 alignment (v3.0) | no change |
| forrestchang/andrej-karpathy-skills | 4 principles → FANG.md | **convergent with gstack's role-based discipline** — promoted from minor to joint-source of the role methodology |
| thedotmack/claude-mem | W2 memory overhaul (v3.1) | no change |
| multica-ai/multica | W3 supervisor (v3.2) | **challenged by Conductor** — we now have two competing coordination patterns to pick between in v4 |
| shiyu-coder/Kronos | out-of-domain | still out |
| **garrytan/gstack** | — | **NEW: role-cohort expansion + cross-model verification + isolated-session parallelism** |

---

## 2. Goals and Non-Goals

### Goals
1. Ship a **research-role cohort** modeled on gstack's shape — at least 9 specialists covering the research sprint lifecycle (plan → retrieve → extract → verify → synthesize → critique → review → publish → reflect).
2. Add a **cross-model verification tier** — when a claim is high-risk or carries a `mutation_warning`, route it through a second LLM family for independent verdict.
3. Implement **Conductor-style isolated-session orchestration** as an *opt-in* alternative to v3.2's asyncio coordination. Users pick the trade-off: speed (asyncio) vs isolation (subprocess).
4. Map the **research-sprint lifecycle** explicitly in the pipeline — each stage has a named specialist and a named verifier-tier-configuration so the trace is self-describing.
5. Add a **role-based review router** — claim kind (quantitative / qualitative / citation / methodological) determines which verifier tiers run. Current pipeline runs all 5 tiers on every claim; router lets cheap claims skip expensive tiers.

### Non-Goals
- **No browser automation** (gstack's Playwright integration). OpenFang is text/arxiv-centric; real web browsing is v5+.
- **No Supabase or external telemetry.** v2.4 observability floor (Gnomon spans + local tracer) stays the ceiling.
- **No multi-user or team features** (gstack targets founders; OpenFang stays single-researcher).
- **No cross-repo CLI shim** (gstack ships `bin/` scripts installable globally; OpenFang's `openfang` CLI already covers this).

---

## 3. Workstreams

### W1 — Research-Role Cohort (9 specialists)

**Motivation.** v3.2 lands 5 specialists; gstack proves 23+ roles work at scale. For OpenFang's narrower domain (AI-paper research), the right cohort size is ~9.

**Cohort** (new specialists in **bold**):

| Role | Lifecycle stage | Primary skill | New in v4 |
| --- | --- | --- | --- |
| ResearchDirectorAgent | plan | — (orchestrator) | **✅** |
| SurveyAgent | retrieve (breadth) | citation-extraction | v3.2 |
| DeepReadAgent | retrieve (depth) | claim-localization | v3.2 |
| ClaimVerifierAgent | verify | counter-example-generation | v3.2 |
| MethodologistAgent | verify (methodology) | reproduction-script | **✅** |
| SynthesisAgent | synthesize | — | v3.2 |
| CriticAgent | critique | peer-review | v3.2 |
| **ThreatModeler** | critique (safety) | — | **✅** |
| **PublisherAgent** | publish | — | **✅** |

**Each specialist declares** (per `SPECIALIST.md` — same frontmatter shape as `SKILL.md`):
- `stage` (one of the 9 lifecycle stages)
- `owned_skills` (which skills it activates by default)
- `verifier_tiers` (which of the 5 verifier tiers to run for its outputs)
- `model_family_preference` (anthropic / openai / either — feeds cross-model routing in W2)
- `cost_ceiling_usd` (per-invocation budget)

**Supervisor integration**: v3.2's supervisor reads the cohort manifest and dispatches to the right specialist per DAG node kind.

**Tests:** cohort discovery (9 specialists load), stage-to-specialist mapping, unknown stage falls through to a default, cost-ceiling enforcement.

### W2 — Cross-Model Verification Tier

**Motivation.** gstack's `/review` (Claude) + `/codex` (OpenAI) pattern proves cross-family verdicts catch a different failure class. Our current pipeline uses one LLM family end-to-end.

**Design.**

New verifier tier configuration per claim:

| Tier | Current | v4 |
| --- | --- | --- |
| 1 Lexical | free | free |
| 2 Mutation (warning) | same-family judge | same-family |
| 3 LLM judge | same-family | **same-family primary; route high-risk to cross-family** |
| 4 Executable | deterministic | deterministic |
| 5 Critic | same-family | **same-family primary; cross-family on disagreement** |
| **5b Cross-model reconcile (NEW)** | — | runs when primary judge + critic disagree |

A "high-risk" claim is one with `mutation_warning=True` OR `executable_passed=False` OR containing quantitative content. The router escalates only those to cross-family; ~70%+ of claims stay single-family (cost-neutral).

**Configuration.** `ClaimVerifier(llm_primary=ClaudeLLM(), llm_secondary=OpenAILLM(), cross_model_on_high_risk=True)`. Default `llm_secondary=None` preserves v3 behavior.

**Tests:** cross-model disagreement triggers 5b reconcile; agreement short-circuits; secondary=None is a no-op.

### W3 — Conductor-Style Isolated-Session Orchestration (opt-in)

**Motivation.** v3.2's asyncio coordination shares a process and a Python namespace — fast but not isolated. Conductor runs each specialist as a *separate Claude Code session* with its own context window; no cross-contamination, no shared state pollution. For long research runs this matters.

**Design.**

Two modes on `Supervisor`:
- `mode="asyncio"` (v3.2 default) — shared process, fast dev feedback, cheap.
- `mode="isolated"` (v4 new) — each specialist runs as a subprocess invoking the `openfang` CLI with a dedicated brief subset. Stdin/stdout JSON-RPC for coordination. Gnomon spans emitted per-subprocess and merged by the supervisor.

**Trade-offs.**

| | asyncio | isolated |
| --- | --- | --- |
| latency | ~100ms coordination | ~500ms per specialist startup |
| isolation | shared Python namespace | full process isolation |
| cost | 1× LLM calls | 1× LLM calls (same) |
| crash recovery | full-pipeline restart | per-specialist restart |
| memory footprint | O(1) | O(N specialists) |

Default stays asyncio; set `OPEN_FANG_SUPERVISOR_MODE=isolated` to flip.

**Tests:** isolated mode runs 3 specialists end-to-end; crashing one specialist fails only that specialist, sibling completes; env-var flip works.

### W4 — Sprint-Lifecycle Labels + Self-Describing Traces

**Motivation.** gstack's think → plan → build → review → test → ship → reflect discipline gives a vocabulary every trace can wear. Our pipeline's Gnomon spans carry `kind` (arxiv.search, extract.claims, etc.) but no higher-level *stage*. Adding stages lets downstream tooling (W4 trajectory export in v3.3) emit training data that RL consumers understand.

**Design.**

- `Span.stage: str` — one of 9 research-sprint stages.
- Scheduler tags each span with the stage derived from the specialist that produced it.
- `GET /v1/supervisor/status` returns current stage + progress per specialist.

**Tests:** every span carries a stage; stage-progress endpoint returns expected shape; trajectory export (v3.3) now includes stages.

### W5 — Role-Based Review Router

**Motivation.** Today every claim hits all 5 verifier tiers. Cheap qualitative claims don't need Tier 4 (executable); quantitative claims *must* hit Tier 4. A router cuts latency + cost without dropping correctness.

**Design.**

`ClaimKindClassifier` labels each claim as `quantitative` / `qualitative` / `citation` / `methodological`. `ClaimVerifier` reads the label and selects the active tiers:

| Claim kind | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 | Tier 5b |
| --- | --- | --- | --- | --- | --- | --- |
| quantitative | ✅ | ✅ | ✅ | ✅ | ✅ | conditional |
| qualitative | ✅ | — | ✅ | — | ✅ | conditional |
| citation | ✅ | — | ✅ | — | ✅ | conditional |
| methodological | ✅ | ✅ | ✅ | — | ✅ | conditional |

**Expected savings**: ~40% reduction in LLM-judge calls on the 20-brief corpus (back-of-envelope from fixture distribution).

**Tests:** classifier accuracy on a labeled fixture; router activates the right tiers; cost-per-brief drops measurably on the 20-brief corpus without faithfulness regression.

---

## 4. Phases + exit criteria

| Phase | Scope | Exit | Tests target |
| --- | --- | --- | --- |
| **v3.*** | (prerequisite) v3.0–v3.4 complete per v3-plan.md | v3 release green | ~320 |
| **v4.0** | W1 cohort manifest + 4 new specialists + `SPECIALIST.md` schema | `openfang specialist list` returns 9; supervisor dispatches by stage | ~345 |
| **v4.1** | W5 claim-kind classifier + router | ≥30% LLM-call reduction on 20-brief corpus; faithfulness ≥ 0.90 preserved | ~360 |
| **v4.2** | W2 cross-model verification tier | cross-family disagreement triggers Tier 5b; agreement short-circuits | ~375 |
| **v4.3** | W3 isolated-session supervisor mode | env-var flip works; crash-isolation integration test green | ~395 |
| **v4.4** | W4 stage labels + self-describing traces | every span has a stage; `/v1/supervisor/status` returns expected shape | ~410 |
| **v4.5** | Release v4 | docs + AGENTS.md updates + v4 dogfood round green | ~410 |

---

## 5. Critical files to add / modify

```
open-fang/
├── v4-plan.md                           ← this file
├── specialists/                         ← NEW (cohort manifest + 9 SPECIALIST.md files)
│   ├── research-director/SPECIALIST.md
│   ├── survey/SPECIALIST.md
│   ├── deep-read/SPECIALIST.md
│   ├── claim-verifier/SPECIALIST.md
│   ├── methodologist/SPECIALIST.md
│   ├── synthesis/SPECIALIST.md
│   ├── critic/SPECIALIST.md
│   ├── threat-modeler/SPECIALIST.md
│   └── publisher/SPECIALIST.md
├── src/open_fang/
│   ├── specialists/                     ← NEW module (mirrors skills/)
│   │   ├── loader.py
│   │   ├── registry.py
│   │   └── schema.py
│   ├── supervisor/                      ← v3.2 extension
│   │   ├── asyncio_runner.py
│   │   └── isolated_runner.py           ← NEW (W3)
│   ├── verify/
│   │   ├── cross_model.py               ← NEW (W2 — Tier 5b)
│   │   └── router.py                    ← NEW (W5)
│   └── observe/
│       └── stages.py                    ← NEW (W4 — lifecycle labels)
```

---

## 6. Techniques and trade-offs

| Technique | Source | Workstream | Chosen |
| --- | --- | --- | --- |
| 23-role skill-cohort pattern (adapted to 9 for research) | gstack | W1 | ✅ |
| `SPECIALIST.md` same-shape-as-`SKILL.md` | ECC + gstack | W1 | ✅ |
| Cross-model verification (Claude ↔ OpenAI) | gstack `/review` + `/codex` | W2 | ✅ |
| Isolated-session orchestration | gstack Conductor | W3 | ✅ opt-in |
| Asyncio coordination (kept as default) | v3.2 + multica | W3 | ✅ default |
| Sprint-lifecycle stage labels | gstack + Karpathy principles | W4 | ✅ |
| Claim-kind routing | OpenFang design | W5 | ✅ |
| Playwright browser automation | gstack | — | ❌ out of scope |
| Supabase telemetry | gstack | — | ❌ out of scope |
| Real-time team WebSocket UI | multica | — | ❌ v5+ |
| Full 23-role cohort | gstack | W1 | ❌ overscope for single-researcher |
| Cross-family for every claim | W2 naive | W2 | ❌ cost |
| Isolated sessions as default | W3 naive | W3 | ❌ too slow for dev loop |

---

## 7. Risks

- **Cohort sprawl.** 9 specialists is manageable; at 15+ the coordination overhead dominates. Mitigation: adding a 10th specialist requires a benchmark showing ≥ 5% improvement on a dedicated eval slice (same discipline as v3.2).
- **Cross-model cost spike.** Naive cross-family verification on every claim doubles LLM cost. Mitigation: W2 only routes high-risk claims (`mutation_warning` / executable_failed / quantitative); the W5 router further narrows this.
- **Isolated-session latency tax.** 500ms × N specialists on a short brief outweighs the isolation benefit. Mitigation: opt-in via env var; document the trade-off clearly in supervisor docs; keep asyncio default.
- **Classifier inaccuracy in W5.** A mis-classified quantitative claim that lands as "qualitative" skips Tier 4 — real regression risk. Mitigation: classifier errors on the labeled fixture must stay < 5%; a claim tagged with numeric tokens auto-escalates to quantitative regardless of classifier verdict.
- **gstack's author context inflates expectations.** Y Combinator's president shipped 23 skills and claims "810× productivity". OpenFang's metric is faithfulness ratio + Pass^k, not LoC. Don't copy gstack's benchmarking story — our eval floors stay on empirical faithfulness.

---

## 8. Open questions

1. **SPECIALIST.md vs SKILL.md schema drift.** The two should share most frontmatter; pick one and carry the other. Default: `SPECIALIST.md` is a *superset* of `SKILL.md` that adds `stage`, `owned_skills`, `verifier_tiers`, `model_family_preference`, `cost_ceiling_usd`.
2. **Secondary LLM provider identity.** Anthropic ↔ OpenAI is the gstack pattern. Should OpenFang also support Gemini / local models? Default: yes, via `LLMProvider` abstraction already present in `harness_core`. Secondary = any provider instance.
3. **Isolated-session IPC protocol.** JSON-RPC stdio (same as MCP server in v2.6) vs a dedicated OpenFang IPC format. Default: reuse the MCP JSON-RPC stdio pipeline for consistency.
4. **Claim-kind classifier implementation.** Rule-based (regex + token features) vs LLM-judged. Default: rule-based for v4.1 (deterministic, cheap); escalate to LLM-judged only for claims the rule classifier labels `ambiguous`.
5. **Stage label granularity.** 9 stages is the sprint-lifecycle baseline. Do we sub-divide (e.g., `retrieve.breadth` / `retrieve.depth`)? Default: flat 9 for v4; revisit only if trajectory-export consumers ask for finer-grained labels.

---

## 9. The one-sentence v4 pitch

> OpenFang v4 turns the pipeline into a **research sprint** with 9 specialist roles, cross-model verification for high-risk claims, and optional isolated-session parallelism — all opt-in, all test-gated, all measured against the existing faithfulness floors.

Ships as: `v3.* green → v4.0 cohort → v4.1 router → v4.2 cross-model → v4.3 isolated supervisor → v4.4 stage labels → v4.5 release.` Test count 262 (current) → ~410 by v4.5.
