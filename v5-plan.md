# OpenFang v5 — Plan

> **Prerequisite:** v3 shipped (v3.0–v3.2 done + remaining v3.3 trajectory export). v4 shipped per [v4-plan.md](v4-plan.md) (9-role cohort, cross-model verification, isolated supervisor, stage labels, claim-kind router). v5 is the post-v4 horizon.

## 0. TL;DR

Fresh research round (2026-04-22) on 10 sources. Most were stable since the prior round; six refresh signals matter for v5:

1. **Hermes Agent v0.10.0 is explicitly agentskills.io compliant** and ships Atropos RL via a `tinker-atropos` submodule. OpenFang v3.0 alignment path is validated; v3.3 trajectory export has a concrete consumer.
2. **claude-mem's MCP tools are canonically `search` / `timeline` / `get_observations`.** OpenFang v3.1 shipped the same 3-tier shape under different names. v5 should add alias endpoints so claude-mem clients drop in.
3. **gstack `/codex` has three cross-model modes**: review gate, adversarial challenge, open consultation. v4 W2 treats cross-model as one mode — v5 lifts it to three.
4. **multica 18.3k★ already supports Hermes as a runtime.** OpenFang should be supportable as a multica agent runtime too; v5 adds the task-assignment adapter.
5. **New awesome-list additions** — ClawBench (browser), Corpus2Skill (navigate-not-retrieve), CORAL (self-evolving multi-agent +3–10×), OptimAI (4-agent optimization 88%). Corpus2Skill is the most transformative for v5.
6. **Repos move fast.** ECC is at v1.10.0 with 183 skills (up from ~150), Hermes at v0.10.0, gstack's cohort keeps growing. v5 needs to formalize OpenFang's own release cadence to match.

Five v5 workstreams emerge. None overthrow v4; they extend it.

---

## 1. Research refresh per source

| Source | Delta vs last round |
| --- | --- |
| affaan-m/everything-claude-code | v1.10.0, 163k★, **183 skills**, Rust ECC 2.0 Alpha control plane, desktop Tkinter dashboard |
| arxiv:2604.05013 Atomic Skills | v1 still current — no change |
| arxiv:2604.18292 Agent-World | confirmed "work in progress", 8B + 14B outperform strong proprietary models on 23 benchmarks |
| VoltAgent/awesome-ai-agent-papers | **new adds**: ClawBench (2604.08523), Corpus2Skill (2604.14572), CORAL (2604.01658), OptimAI (2504.16918), RecSim (2604.09549) |
| nousresearch/hermes-agent | **v0.10.0 (2026-04-16); agentskills.io compliant; Atropos via `tinker-atropos` submodule** |
| forrestchang/andrej-karpathy-skills | 71.4k★, still a `CLAUDE.md` guidelines doc (4 principles) |
| thedotmack/claude-mem | **3 canonical MCP tool names: `search` / `timeline` / `get_observations`**; Python-via-uv for vectors; AGPL-3.0 |
| multica-ai/multica | 18.3k★, **supports Claude Code / Codex / OpenClaw / OpenCode / Hermes / Gemini / Pi / Cursor** as agent runtimes; no MCP yet |
| shiyu-coder/Kronos | still out-of-domain (K-line forecasting, AAAI 2026) — skip |
| garrytan/gstack | 79.4k★, **22 specialist roles** (not 23), Conductor runs 10-15 parallel sessions, **`/codex` has 3 modes: review gate / adversarial challenge / open consultation** |

---

## 2. Goals and Non-Goals

### Goals
1. **Navigate-not-retrieve skill tree** (Corpus2Skill pattern): hierarchical skill organization the agent traverses, replacing the flat registry.
2. **claude-mem MCP tool-name parity**: expose `memory.search` / `memory.timeline` / `memory.get_observations` alongside the existing 4 read-only tools so claude-mem clients talk to OpenFang interchangeably.
3. **Multica runtime adapter**: OpenFang installable as a multica agent (task-assignment model: enqueue / claim / start / complete hooks).
4. **Hermes–Atropos trajectory pipeline**: formalize v3.3 export as the Atropos-compatible feed; add a schema test against Hermes's `tinker-atropos` submodule expectations.
5. **Three-mode cross-model verification**: v4 W2 upgraded from single-mode to gstack's 3-mode pattern (review gate / adversarial challenge / open consultation).
6. **Rolling weekly feed cron**: v2.7 shipped the parser; v5 wires the scheduler + auto-KB-import.

### Non-Goals
- **No browser automation** (ClawBench's domain). Text/arxiv stays the substrate.
- **No Rust control plane** (ECC 2.0 Alpha direction). Python + FastAPI stays the stack.
- **No cohort expansion beyond v4's 9 specialists** without a measured benchmark per new role.
- **No live Hermes/multica integration** in CI — those need real clients + keys. Ship the adapters; smoke-test manually.
- **No Corpus2Skill navigation for non-skill KB papers** — skill tree only; paper KB stays flat FTS5.

---

## 3. Workstreams

### W1 — Navigate-Not-Retrieve Skill Tree (Corpus2Skill pattern)

**Source.** arxiv:2604.14572 Corpus2Skill — distills corpora into hierarchical skill trees the agent navigates with deterministic moves (e.g., `cd category/subcategory`) rather than retrieving-and-ranking.

**Why v5.** OpenFang's skill registry is flat: `activate(query)` returns top-k by token overlap. With 5 curated + N learned skills, flat is fine. At 50+ skills (realistic after a few months of evolving-arena use) the activation noise swamps signal. Hierarchy scales.

**Design.**
- Extend `SkillLoader` to respect nested directories under `skills/` — `skills/verify/mutation/SKILL.md`, `skills/verify/executable/SKILL.md`, etc.
- New `SkillTree` class (replaces `SkillRegistry` as the default) — supports `.navigate(path)`, `.children(path)`, `.describe(path)`.
- Activation becomes: LLM-choose-a-child-at-each-level (2-hop average) instead of overlap-rank across all leaves.
- Back-compat: flat `skills/` keeps working; `SkillTree` treats them as children of root.

**Tests.** Unit: navigate happy path, descend into missing child returns None, cycles rejected. Integration: 9-skill hierarchy activates the right leaf on a benchmarked query set.

### W2 — claude-mem Tool-Name Parity (Drop-in MCP compatibility)

**Source.** thedotmack/claude-mem — the 3 canonical tool names are `search`, `timeline`, `get_observations`. OpenFang v3.1 shipped the same three-tier memory architecture under different endpoint names (`/v1/memory/timeline`, `/v1/memory/observation/{id}`).

**Why v5.** Any tool built against claude-mem's MCP schema (and there's an ecosystem of them — the Claude Code plugin directory lists a dozen) works against OpenFang unchanged. Zero migration cost for claude-mem users adopting OpenFang.

**Design.**
- Add `memory.search` / `memory.timeline` / `memory.get_observations` to the MCP server (v2.6 shipped 4 tools; v5 adds 3 more under namespace `memory.*`).
- `memory.search` is new — FTS5 over `compact_summary + detail_summary` (v3.1 schema has both).
- `memory.timeline` mirrors v3.1's `/v1/memory/timeline` endpoint.
- `memory.get_observations` takes a list of ids (note plural — matches claude-mem's plural), returns a list.

**Tests.** Unit: each tool's input schema matches claude-mem's shape. Integration: round-trip through the stdio MCP server returns expected JSON. Smoke: point a real claude-mem client at OpenFang's MCP server — expected to "just work".

### W3 — Multica Runtime Adapter

**Source.** multica-ai/multica — task-assignment model (enqueue → claim → start → complete/fail), supports 8 agent runtimes including Hermes. No MCP yet.

**Why v5.** If OpenFang becomes a multica runtime, teams using multica's web-UI task board can dispatch research briefs to OpenFang identically to how they dispatch coding tasks to Claude Code or Codex. This is the multi-user entry point OpenFang explicitly deferred in v3/v4 non-goals.

**Design.**
- `src/open_fang/adapters/multica.py` — implements multica's runtime protocol (WebSocket-based per their README).
- `openfang multica serve` CLI subcommand — starts a multica-compatible agent process that registers with a multica server URL passed via env.
- Each brief dispatched by multica → one `OpenFangPipeline.run()` → progress streamed via multica's WebSocket protocol.

**Tests.** Unit: protocol message encoder/decoder. Integration: mock multica server sends a brief, adapter processes it, responds with correct progress events. No live multica required.

### W4 — Hermes–Atropos Trajectory Pipeline

**Source.** nousresearch/hermes-agent v0.10.0 ships `tinker-atropos` submodule for RL training.

**Why v5.** v3.3 in the v3 plan lists "trajectory export" as a phase; now we have a concrete schema target (Hermes's Atropos expectations) to validate against. v5 formalizes this into a cron-style export + a manifest format Hermes can ingest.

**Design.**
- `openfang trajectory export --format atropos --to path/manifests.json` — batch-exports every `PipelineResult` from a date range.
- Manifest schema exactly matches `tinker-atropos` inputs (verify against the submodule's README).
- Optional: `--include-weak` flag emits failing trajectories separately (Agent-World shows these are the valuable training data).

**Tests.** Schema-validation test against a fixture Atropos trajectory (hand-authored from the submodule's README). Round-trip: export → re-parse → schema-valid.

### W5 — Three-Mode Cross-Model Verification (gstack `/codex` pattern)

**Source.** garrytan/gstack — `/codex` has 3 modes: review gate (pass/fail), adversarial challenge (attack the output), open consultation (advisory opinion).

**Why v5.** v4 W2 proposed cross-model as one mode (secondary judge on high-risk claims). gstack's three modes are independently valuable:
- **Review gate**: hard veto if the secondary rejects.
- **Adversarial challenge**: secondary attempts to construct a counter-example; failure means "claim survives attack".
- **Open consultation**: secondary writes a margin comment for the synthesizer's next turn, not a verdict.

**Design.**
- `src/open_fang/verify/cross_model.py` grows three method signatures: `review_gate()`, `adversarial_challenge()`, `open_consultation()`.
- `ClaimVerifier` accepts a `cross_model_mode` config: one of `"review"`, `"adversarial"`, `"consultation"`, or a tuple (default `("review", "adversarial")` for high-risk claims).

**Tests.** Unit: each mode emits the right verdict shape; consultation result is advisory (no veto). Evaluation: mutation-corpus catch rate with mode=adversarial vs mode=review; adversarial should catch ≥ the mutation tier does alone.

### W6 — Rolling Weekly Feed Cron

**Source.** v2.7 shipped `eval/feed.py` parser; live pulling was out of scope.

**Why v5.** The awesome-list has added 5 papers since the v2.7 feed parser shipped. Without an auto-pull, the corpus stays frozen at 50 briefs while the literature compounds.

**Design.**
- `src/open_fang/eval/feed_cron.py` — module-level scheduler (no OS-level cron dependency; a thread + sleep loop). Configurable interval via `OPEN_FANG_FEED_INTERVAL_HOURS` (default 168 = weekly).
- On each tick: WebFetch the awesome-list markdown → `parse_feed` → for each new arxiv ID: WebFetch abstract → upsert into KB as `kind=arxiv` paper.
- Dedup: skip IDs already in KB (checked via `kb.list_paper_ids()`).
- Idempotent: safe to run many times.
- Opt-in: not started by default in `make run`; needs explicit `OPEN_FANG_FEED_CRON=1` to activate.

**Tests.** Unit: cron logic with a mocked clock + mocked WebFetch; dedup test. Integration (network-marked): real pull skipped in CI unless `-m network`.

---

## 4. Cross-cutting concerns

### CC-1 — Release cadence formalization

Everyone in the ecosystem updates weekly-to-monthly. OpenFang should match:
- **Weekly**: feed cron (W6) pulls new papers.
- **Bi-weekly**: evolving arena (v2.1) runs; learned skills promoted on disk.
- **Monthly**: docs refresh; agentskills.io + Hermes + multica compat spot-checked.
- **Quarterly**: research-refresh round like this one; new-version plan written.

Document this in `docs/release-cadence.md` — one page.

### CC-2 — Kronos stays rejected

Third research round confirms it's financial forecasting. Noted permanently in `docs/research-log.md` so we don't re-check.

### CC-3 — Corpus2Skill for KB (explicit non-goal)

Paper KB stays flat FTS5. Navigate-not-retrieve applies to the **skill tree** only — the paper corpus benefits more from full-text search than from hierarchy at our scale.

---

## 5. Phases

| Phase | Scope | Exit criteria | Test target |
| --- | --- | --- | --- |
| **v4.*** (prereq) | v4.0–v4.5 green per v4-plan.md | v4 released | ~410 |
| **v5.0** | W2 claude-mem tool-name parity | 3 new MCP tools round-trip through stdio | ~430 |
| **v5.1** | W1 skill tree (hierarchy + navigate) | 9-skill hierarchy activates correct leaf | ~450 |
| **v5.2** | W5 three-mode cross-model verification | adversarial catch ≥ mutation baseline | ~465 |
| **v5.3** | W4 Atropos trajectory pipeline | schema-validates against fixture | ~475 |
| **v5.4** | W6 rolling feed cron | ≥ 2 new arxiv IDs imported in a 168h fixture run | ~485 |
| **v5.5** | W3 multica runtime adapter | mock multica server dispatches a brief end-to-end | ~500 |
| **v5.6** | Release v5 + CC-1 cadence doc | docs refreshed; dogfood on the now-expanded corpus | ~500 |

Target: 361 (end of v3.2) → ~500 by v5.6. Approximately 140 new tests over 6 phases.

---

## 6. Trade-offs

| Technique | Source | Workstream | Chosen |
| --- | --- | --- | --- |
| Navigate-not-retrieve hierarchical skills | Corpus2Skill (2604.14572) | W1 | ✅ |
| claude-mem MCP tool-name parity | thedotmack/claude-mem | W2 | ✅ |
| Multica runtime adapter | multica-ai/multica | W3 | ✅ |
| Hermes–Atropos trajectory export | nousresearch/hermes-agent | W4 | ✅ |
| Three-mode cross-model verification | gstack `/codex` | W5 | ✅ |
| Weekly feed cron | awesome-list velocity | W6 | ✅ opt-in |
| Claude Code slash-command aliases | gstack pattern | — | ❌ v6 (we're not a coding agent) |
| Browser agent (ClawBench) | 2604.08523 | — | ❌ non-goal |
| Rust control plane (ECC 2.0 Alpha) | ECC v1.10.0 | — | ❌ stack stability |
| Corpus2Skill navigation for paper KB | Corpus2Skill | — | ❌ FTS5 wins at our scale |
| Live multica WebSocket server-bindings in CI | multica | W3 | ❌ mock only |
| RL training loop inside OpenFang | Hermes Atropos | — | ❌ export only, no training |
| Self-evolving multi-agent breeding (CORAL) | 2604.01658 | — | ⏸ v6 candidate |
| OptimAI-style 4-agent optimization pipeline | 2504.16918 | — | ⏸ v6 candidate — narrow domain |

---

## 7. Risks

- **Hierarchy inversion in W1.** If categories are chosen poorly, the tree activates the wrong subtree more often than flat overlap. Mitigation: the SkillTree parser validates category depth ≤ 3 and leaf count per category ≤ 12 (gstack's shape). A tree that fails these caps falls back to flat.
- **MCP tool-name collision in W2.** If a client uses `search` and expects claude-mem's schema but we've also registered `kb.search`, name resolution becomes ambiguous. Mitigation: use namespaced forms (`memory.search` vs `kb.search`) and document the aliasing explicitly.
- **Multica protocol drift in W3.** multica's WebSocket protocol may change between versions. Mitigation: pin a specific multica version in the adapter's docstring; add a compatibility matrix.
- **Atropos schema drift in W4.** Hermes submodule is new; schema may evolve. Mitigation: adapter is thin; regenerate schema fixture on Hermes version bumps.
- **Adversarial challenge overhead in W5.** Adversarial mode is expensive (second LLM generates counter-example, primary re-evaluates). Mitigation: only invoke on claims that pass mutation Tier 2 warning AND have `executable_passed=False` OR `quantitative` claim-kind.
- **Feed cron runaway in W6.** A misparsed feed could flood the KB with bad entries. Mitigation: per-run hard cap of 20 new imports; dry-run flag; visible audit log.

---

## 8. The one-sentence v5 pitch

> OpenFang v5 moves from an isolated research agent to a **first-class citizen of the agentskills.io / claude-mem / multica / Hermes ecosystem**: claude-mem clients talk to us unmodified, multica teams can assign briefs to us as a runtime, Hermes trainers can consume our trajectories, gstack-style 3-mode cross-model verification is live, and the skill library navigates hierarchically at scale.

Ships as: `v4.* green → v5.0 claude-mem parity → v5.1 skill tree → v5.2 three-mode cross-model → v5.3 Atropos export → v5.4 feed cron → v5.5 multica adapter → v5.6 release`. Test count ~361 (current v3.2) → ~410 (v4 complete) → ~500 (v5.6).
