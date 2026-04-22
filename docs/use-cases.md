# What is OpenFang for?

A short, honest answer to "should I use OpenFang for my problem?"
For deep architecture details see [docs/architecture.md](architecture.md);
for HTTP/CLI mechanics see [docs/fang-cli.md](fang-cli.md).

---

## In one paragraph

OpenFang is a **verifier-first autonomous research agent**, specialized for
the AI / agentic-AI / harness-engineering literature. You hand it a research
question; it plans a DAG of fetch-and-reason steps, pulls papers from arXiv,
extracts and verifies claims through a 5-tier pipeline (lexical → mutation
→ LLM-judge → executable → cross-channel), promotes verified claims into a
local SQLite+FTS5 knowledge base with a weighted citation graph, and emits
a structured report whose every claim is anchored to evidence with a
faithfulness ratio. Synthesis is rule-based; the LLM is used for planning
and judging, not for free-form prose.

That last sentence is the differentiator: OpenFang would rather refuse to
say something than say it without grounded evidence.

---

## Who it's for

- **AI/ML engineers and researchers** who want a literature-review pipeline
  that won't fabricate citations or numbers.
- **Agent/harness builders** who need a reference architecture for DAG
  planning, layered verification, persistent memory, and MCP integration —
  and who want runnable code rather than blog posts.
- **Curriculum designers and teachers** who want an end-to-end example of a
  TDD-built, observability-instrumented agentic system (612 tests, every
  pipeline stage traced, every claim attributed).

If you want a chatbot that "feels like" Claude or ChatGPT, OpenFang is the
wrong tool. See [What it's *not* good for](#what-its-not-good-for) below.

---

## Core use cases

### 1. Verified literature review on a narrow topic

You have a question like "what's the state of long-context attention as of
2026?" and you want a report whose every numeric claim is backed by a
specific paper, with the faithfulness ratio printed in the footer.

```bash
fang server start
fang research "Compare Mamba, RWKV, and YaRN on long-context retrieval —
                methods, benchmarks, and known failure modes."
```

The pipeline plans the DAG, fetches arXiv evidence, extracts ~5–20 claims,
runs them through the 5-tier verifier, promotes the survivors into the KB,
and returns a `Report` JSON with `faithfulness_ratio` and per-claim evidence
IDs. Cross-channel verification (claim must appear in abstract ∧ body ∧
table) catches the most common hallucination class — bogus benchmark
numbers.

> ⚠️ Live mode requires `ANTHROPIC_API_KEY`. Without it, the server runs
> the same pipeline but with `MockSource` + `MockLLM`, so output is
> structurally correct but semantically synthetic. See `GET /v1/info`.

### 2. Building a personal citation graph

After a few research runs, your local KB accumulates papers, citations, and
typed edges (`cites`, `extends`, `compares-to`, `benchmarks-on`). The
weighted multi-hop walker finds non-obvious connections.

```bash
curl http://127.0.0.1:8010/v1/kb/papers | jq '.papers[] | {id, title}'
curl http://127.0.0.1:8010/v1/kb/graph?focus=arxiv:2401.12345 | jq
open http://127.0.0.1:8010/viewer/        # interactive Cytoscape view
```

Useful when you've read enough in a subfield that paper IDs blur together
and you need to see the actual citation topology.

### 3. Hosting a read-only MCP server for other agents

OpenFang exposes 7 read-only MCP tools (skill listing, KB search, memory
timeline) over stdio. Plug it into Claude Code, Cursor, or any
MCP-compatible host and your agent can search your verified-claim KB during
its own work.

```bash
fang mcp serve     # stdio MCP server (claude-mem `memory.*` parity)
```

Practical when you want a Claude Code session to ground answers in a
literature you've already curated, without re-fetching.

### 4. Teaching or referencing the architecture

The repo is a working artifact of several patterns that are hard to find
runnable examples of:

- **DAG-Teams orchestration** ([planner/llm_planner.py](../src/open_fang/planner/llm_planner.py),
  [scheduler/engine.py](../src/open_fang/scheduler/engine.py)): Phase-1
  LLM planner emits JSON DAG → Phase-2 deterministic scheduler executes it
  with permission gates and chaos injection.
- **5-tier verifier** ([verify/](../src/open_fang/verify/)): each tier is a
  separate file you can read in isolation.
- **Three-tier progressive-disclosure memory** ([memory/store.py](../src/open_fang/memory/store.py)):
  ≥5× token reduction on replay, gated by a coverage test.
- **HAFC-lite primitive failure attribution** ([attribution/](../src/open_fang/attribution/)):
  rules-first per-primitive blame assignment for debugging agent failures.
- **Skill library aligned with agentskills.io** ([skills/](../src/open_fang/skills/)):
  schema + activation + evolving-arena extraction.

Read the source — it's the documentation.

### 5. Generating training data for RL fine-tuning

OpenFang exports trajectories in Atropos-compatible JSONL — every span in a
research run becomes one row of (state, action, reward, evidence). Useful
as a stepping stone toward "self-improving research agent" experiments.

```bash
fang trace validate trajectories.jsonl
```

### 6. Adversarial robustness testbed

Built-in chaos hooks (`OPEN_FANG_CHAOS_MODE=network_drop:0.2`), security
probes (4 categories), red-team prompts, and a fragility-matrix scanner.
Useful if you're researching how agentic systems fail and want a
reproducible harness rather than building one yourself.

### 7. Self-research loop

OpenFang can research its own plan files (`v6.5`). Useful only if you're
exploring meta-research patterns — most users won't need this — but it's a
working example of an agent recursively analyzing its own roadmap.

---

## What it's *not* good for

| Use case | Better tool |
|---|---|
| Chat / conversation / Q&A | Claude, ChatGPT, perplexity.ai |
| General-purpose web research | perplexity.ai, exa.ai, gemini deep research |
| Real-time information (news, prices) | A search engine |
| Domains outside AI/agentic-AI literature | Pre-built RAG over your domain corpus |
| Hand-wavy creative writing | Any base LLM |
| Anything where you want fluent prose | OpenFang's synthesis is template-based on purpose |

**Two specific anti-recommendations:**

1. *Do not* use OpenFang as a Q&A bot. The HTTP REPL POSTs each line as a
   research brief; the pipeline is heavyweight (planning + fetching +
   verifying takes seconds even on cached papers). Use `claude` for chat.
2. *Do not* expect creative output. The synthesizer is deliberately
   rule-based to avoid the LLM-prose-makes-things-up failure mode. If you
   want a paragraph that *flows*, you'll be disappointed.

---

## How it compares to nearby tools

| Tool | What it gives you | What OpenFang adds |
|---|---|---|
| **Perplexity / Exa** | Fast web RAG, fluent answers | Local KB, evidence IDs per claim, mutation/executable verification, citation-graph topology, MCP surface |
| **Elicit / Consensus** | Curated paper search + summary | Open code, runnable locally, custom verifier tiers, no per-query fees |
| **arXiv Sanity / Connected Papers** | Citation-graph browser | Same plus a research pipeline that *fills* the graph |
| **Claude / ChatGPT with web search** | Conversational research | Faithfulness ratio, deterministic scheduler, persistent memory across sessions |
| **A custom LangChain/LlamaIndex stack** | Full flexibility | Working DAG planner, 5-tier verifier, and skill library you'd otherwise build yourself |

OpenFang is closest to "the research agent equivalent of a typed,
test-covered codebase" — slower than a conversational tool, much more
auditable.

---

## Pick a starting point

| You want to... | Start here |
|---|---|
| Try the REPL on a real paper | [docs/fang-cli.md](fang-cli.md) → `fang research "..."` |
| Understand the pipeline architecture | [docs/architecture.md](architecture.md) |
| Read the system design and trade-offs | [docs/architecture-tradeoff.md](architecture-tradeoff.md) |
| Inspect a specific verifier tier | [src/open_fang/verify/](../src/open_fang/verify/) |
| Hook up an MCP host | [README.md §MCP tools](../README.md) → `fang mcp serve` |
| Run the pipeline programmatically (no HTTP) | [src/open_fang/pipeline.py](../src/open_fang/pipeline.py) |
| See every release's deltas | [README.md status table](../README.md#status) |
