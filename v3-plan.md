# OpenFang v3 — Plan

## 0. TL;DR

v2 is 5/7 phases complete (v2.0–v2.5 done; v2.6 MCP + v2.7 release remain). Current state: 245 tests, 5-tier verifier, citation graph + random-walk synthesis, 5-skill library + evolving arena, security probes + chaos hooks + red-team. The research round for v3 uncovered five new signal sources; two are transformative, two are aligning, one is out-of-domain.

Transformative finding: **`nousresearch/hermes-agent` IS the Hermes pattern** — a production self-improving-skill-library agent with `agentskills.io` open standard, FTS5 session search, trajectory compression for RL training, and Atropos RL integration. OpenFang v2.1 designed this from the literature; Hermes Agent shipped it. The v3 question becomes *"do we converge with this open standard, or stay bespoke?"* — answer is converge.

Other transformative finding: **`thedotmack/claude-mem`** ships the progressive-disclosure memory pattern (~10× token savings via compact index → timeline → full details), captures tool-use observations not raw messages, SQLite + Chroma hybrid search. OpenFang's working buffer is thin by comparison; v3 overhauls memory along these lines.

Aligning: **`multica-ai/multica`** shows a real supervisor/assignment multi-agent pattern. OpenFang's §Multi-Agent coverage is zero; v3 closes that gap with a vertical slice of specialist skill-agents coordinated by a supervisor.

Minor: **`forrestchang/andrej-karpathy-skills`** is a 4-principle guidelines doc (Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution). Not a library — fold into `FANG.md` persona defaults.

Out-of-domain: **`shiyu-coder/Kronos`** is a foundation model for financial candlesticks (20k★, MIT). Not relevant to an AI-paper research agent. Rejected.

---

## 1. Research inputs (all fetched 2026-04-22)

### 1.1 Nous Research / `hermes-agent`

- **License:** MIT. Python 87.6% + TypeScript 8.2%.
- **Shape:** `agent/ skills/ tools/ plugins/ gateway/ ui-tui/ web/ docker/ tests/`. 40+ integrated tools, terminal + web UI.
- **Loop:** closed learning loop with *autonomous skill creation after complex tasks* + *skills self-improve during use*. Matches OpenFang v2.1 EvolvingArena shape exactly, one abstraction layer higher.
- **Open standard:** `agentskills.io` for skill interop across frameworks. **This is the canonical format going forward.**
- **Memory:** agent-curated memory with periodic nudges, FTS5 session search, LLM-powered summarization for cross-session recall.
- **Self-improvement:** trajectory compression for training future models; Atropos RL environment integration. Explicit RL training path, which OpenFang v2 deliberately avoided.

→ **v3 action**: (a) verify OpenFang's `SKILL.md` format is bi-directionally compatible with `agentskills.io` and port if not; (b) add trajectory-export format compatible with Atropos so OpenFang traces become RL training data without OpenFang itself needing to run RL.

### 1.2 `thedotmack/claude-mem`

- **License:** AGPL-3.0 (for main code) + PolyForm Noncommercial 1.0.0 (for ragtime/). **Copy-code restrictions apply; we adopt the architecture, not the source.**
- **TS 82.6% / JS 10.8% / Shell / HTML.** Worker service on port 37777 with web UI.
- **Five lifecycle hooks**: SessionStart / UserPromptSubmit / PostToolUse / Stop / SessionEnd — captures tool-use observations, not raw transcripts.
- **Storage**: SQLite for observations + Chroma vector DB for hybrid search. Scoped per project + session.
- **Progressive disclosure (the headline idea)**: three-layer workflow — compact index (~50–100 tokens) → chronological timeline → full details (~500–1k tokens). **Claims ~10× token savings** by filtering before fetching.
- **4 MCP tools** (search, timeline, get_observations): not a full MCP server, but MCP-adjacent.

→ **v3 action**: OpenFang's `WorkingBuffer` + `ContextAssembler` are thin. Replace with a three-tier progressive-disclosure stack inspired by claude-mem (but clean-room written — AGPL). Capture tool-use observations from the scheduler's Gnomon spans directly. Offer the same 3 MCP tools (search / timeline / get_observations) as part of v2.6 MCP export.

### 1.3 `multica-ai/multica`

- **Stack:** Next.js 16 frontend + Go backend (Chi, sqlc, WebSocket) + Postgres 17 + pgvector. Heavier than OpenFang's stack.
- **Coordination:** *supervisor/assignment-based*. User creates issue → assigns to agent → agent autonomously claims + executes + reports. No peer-to-peer handoffs, no swarm. WebSocket for real-time progress.
- **Agent registry**: web UI (Settings → Agents) specifying runtime / provider / name. Auto-detects CLIs on PATH.
- **Novel vs competitors (per its README)**: reusable skills system, multi-user team design, workspace isolation, vendor-neutral + self-hosted.

→ **v3 action**: adopt the *pattern* not the stack. OpenFang's scheduler already has an assignment model at the node level; extending it to agent-level means each specialist (SurveyAgent, DeepReadAgent, ClaimVerifierAgent, SynthesisAgent, CriticAgent) becomes an independent runtime unit supervised by the existing pipeline. Minimal new infra: Python `multiprocessing` pool or `asyncio.gather` over subagents that each own one DAG node kind.

### 1.4 `forrestchang/andrej-karpathy-skills`

- MIT. Not a skill library despite the name — a 4-principle guidelines doc: Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution.

→ **v3 action**: fold these as quality principles into `FANG.md` persona defaults. Low-lift, one-line addition.

### 1.5 `shiyu-coder/Kronos`

- MIT. 20k★. Foundation model for financial K-line forecasting, tokenizer + decoder-only transformer, 4.1M–499M params.

→ **v3 action**: skip. Out-of-domain. Noted as researched-and-rejected so future planning rounds don't re-check.

---

## 2. Goals and Non-Goals

### Goals
1. Converge the OpenFang skill format with **`agentskills.io`** so OpenFang skills run under `hermes-agent` and vice-versa.
2. Replace `WorkingBuffer` + `ContextAssembler` with a **progressive-disclosure memory** tier (compact index → timeline → full details) backed by Gnomon-span observations.
3. Ship a **supervisor + specialist-subagents** coordination slice (Python-native, no Go/Postgres rewrite).
4. Emit **trajectory-export format** compatible with Atropos so OpenFang traces are reusable as RL training data.
5. Finish v2.6 (MCP bidirectional) and v2.7 (release) before v3 proper starts — those are prerequisites.

### Non-Goals
- **No OpenFang-run RL training.** Export trajectories; let upstream trainers consume. Prompt-only stays the primary mode.
- **No Go/Postgres/Next.js rewrite.** Python + SQLite + FastAPI is the stack.
- **No AGPL code adoption.** Learn from claude-mem's architecture; write clean-room.
- **No multi-tenant yet** (stays v4).
- **No real-time WebSocket UI** in v3; the `/v1/kb/graph` viewer plus a new `/v1/memory/timeline` endpoint are enough.

---

## 3. Workstreams

### W1 — agentskills.io alignment + Hermes interop

**Payoff**: OpenFang skills become portable to `hermes-agent` and back. External skill corpora instantly usable.

**Steps:**
- Spec check: fetch the `agentskills.io` current schema. Diff against OpenFang's `SKILL.md` frontmatter (`name`, `description`, `origin`, `confidence`). Add missing fields, deprecate divergences.
- `SkillLoader.load_from_hermes()` — optional import path that understands Hermes-shipped skills.
- Export path: OpenFang curated skills published to a shared manifest so Hermes installs see them.

**Tests:** schema-validation round-trip against fixtures from Hermes's `skills/`; a learned skill written by OpenFang's extractor passes Hermes's loader and vice-versa.

### W2 — Progressive-disclosure memory

**Payoff**: ~10× token savings on long sessions (claude-mem's own claim); tool-use observations become first-class.

**Steps:**
- Replace `WorkingBuffer` with a three-tier stack:
  - **Tier A — compact index**: ~50–100 tokens, one line per session observation + timestamp. Always in context.
  - **Tier B — chronological timeline**: paginated list of observation summaries. Fetched on demand when the agent wants to recall a past decision.
  - **Tier C — full details**: the raw Gnomon span + evidence + claim, fetched per-id only when needed.
- Observation capture: scheduler's `SpanRecorder` already emits a Gnomon span per node. Add a `MemoryStore` subscriber that LLM-summarizes each span into a Tier A line + Tier B entry, stored in a new SQLite table.
- Endpoints: `GET /v1/memory/timeline` + `GET /v1/memory/observation/{id}` (plus MCP-tool variants for external consumers).
- Persona stays in `FANG.md`, untouched.

**Tests:** 10-turn rolling-window gives ≥ 5× token reduction vs raw-transcript baseline; lookup round-trips.

### W3 — Supervisor + specialist subagents

**Payoff**: fills OpenFang's §Multi-Agent gap with a minimal, Python-native vertical slice.

**Steps:**
- One `Supervisor` class orchestrates specialist subagents. Each specialist wraps one DAG node kind (search.arxiv, extract.claims, verify.claim, synthesize.briefing) and runs in its own `asyncio` task or `multiprocessing` worker.
- Registry via Python entry points (reusing the existing `openfang skill list` pattern).
- WebSocket-free: status streaming via Gnomon span emission + a new `GET /v1/supervisor/status` poll endpoint.
- Minimum specialists: `SurveyAgent`, `DeepReadAgent`, `ClaimVerifierAgent`, `SynthesisAgent`, `CriticAgent` — the five named in [plan.md §3.2](plan.md).

**Tests:** integration test showing a brief dispatched to 5 specialists completes end-to-end; a failing specialist is isolated without taking down its siblings.

### W4 — Trajectory export for RL data

**Payoff**: OpenFang traces become training data for *future* agents without OpenFang itself needing GPUs.

**Steps:**
- `openfang trace export --format atropos > trajectories.jsonl` — CLI subcommand emitting one trajectory per pipeline run, fields compatible with Atropos's expected schema (verify against Hermes's repo).
- Include: brief, plan DAG, node sequence, tool-use span, final report, final `faithfulness_ratio`, all `mutation_warning` flags, all `executable_passed` verdicts.

**Tests:** a schema test against a fixture Atropos trajectory; a round-trip test confirming the exported file loads without schema errors.

### W-CC — Minor cross-cuts

- Add Karpathy's 4 principles as `FANG.md` persona-seed additions (one paragraph).
- Note Kronos as researched-and-rejected in `docs/research-log.md` so we don't re-investigate.
- Update `README.md` + `AGENTS.md` with the new interop story.

---

## 4. Phases + exit criteria

| Phase | Scope | Exit |
| --- | --- | --- |
| **v2.6** (unchanged) | MCP bidirectional | Claude Code / Cursor / Codex can invoke `skill.list`, `skill.run`, `kb.search`; `MCPSpecSource` imports an MCP manifest into KB |
| **v2.7** (unchanged) | Release v2 | AGENTS.md + decontam pass + eval corpus ≥ 50 briefs |
| **v3.0** | W1 agentskills.io alignment | Round-trip Hermes-Agent import + export |
| **v3.1** | W2 progressive-disclosure memory | 5× token reduction on 10-turn rolling fixture |
| **v3.2** | W3 supervisor + subagents | 5-specialist dispatch green end-to-end |
| **v3.3** | W4 trajectory export | Atropos schema round-trip |
| **v3.4** | W-CC + release v3 | README + AGENTS updated; dogfood round green |

Test count target: 245 (v2.5) → ~320 by v3.4.

---

## 5. Open questions

1. **agentskills.io spec version**. Hermes Agent references it; we need the exact schema URL to diff. Action: inspect `nousresearch/hermes-agent` `agent/skills/` tree before W1 starts.
2. **Clean-room AGPL boundary.** Reading claude-mem's code to learn the pattern is fine; copying code is not. Action: all W2 work references only the README + public architecture diagrams.
3. **Specialist subagent IPC.** `asyncio` vs `multiprocessing` vs subprocess — default to asyncio (shared-process, fast dev feedback) unless a specialist imports an expensive module (e.g., a LaTeX parser).
4. **Trajectory schema compatibility.** Until we see Atropos's actual format, v3.3 may need a two-step: emit a generic JSONL, then add a thin adapter layer.
5. **Kronos.** Re-check in v4 only if OpenFang pivots into a domain that needs financial time-series. Noted.

---

## 6. Risks

- **Hermes schema drift.** agentskills.io is an *open standard* which means it evolves. Mitigation: pin to a specific spec version in OpenFang's loader; upgrade on explicit opt-in.
- **Progressive-disclosure cost.** Tier B/C reads via MCP or endpoint require an LLM-summary call per observation captured — budget risk on long sessions. Mitigation: cache LLM summaries in SQLite; throttle per-session summary count.
- **Subagent sprawl.** Five specialists is lean; adding more without discipline costs more than it earns. Mitigation: new specialists require a benchmark showing ≥ 5% improvement on a dedicated eval slice.
- **AGPL contamination.** Inadvertently reading claude-mem source and reusing idioms risks license issues. Mitigation: W2 engineers read only README + blog posts; any code reference is documented with attribution.
