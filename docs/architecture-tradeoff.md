# Architecture Trade-offs

Rejected alternatives, with rationale. See [../plan.md](../plan.md) §5 for the full technique table.

## Orchestration: DAG Teams vs. ReAct

**Chose** DAG Teams (Phase-1 LLM plan → Phase-2 deterministic scheduler).
**Rejected** single-loop ReAct.
- ReAct loses coherence on long-horizon research; a mis-fetched PDF poisons downstream reasoning without clear attribution.
- Node-local retries are impossible in a single loop.

## Multi-agent coordination

**Chose** typed subagents with bounded inputs/outputs.
**Rejected** free-form multi-agent chat (AutoGen/CrewAI shape).
- Free-form chat is the orchestration-fragility mode SemaClaw explicitly fixes.

## Citation graph store

**Chose** SQLite + FTS5 for v1.
**Rejected** Neo4j.
- SQLite meets needs at zero ops cost for the expected corpus size.
- Revisit at >100k papers or when cross-paper graph queries dominate the workload.

## Reasoning pattern

**Chose** Plan-and-Solve + structured DAG + Chain-of-Verification.
**Rejected** Tree of Thoughts / LATS for planning.
- 5–10× cost without measurable win for most research briefs.
- Reserve for the rare "compare N synthesis paths" case.

## Self-improvement

**Chose** v2 skill library (Hermes/Voyager shape).
**Rejected** v1 full Autogenesis self-modification of the scaffold.
- Unsafe without a mesa-guard; push to v3+.

## Observability

**Chose** Gnomon-shape primitive spans (consume the schema, don't build the full HIR).
**Rejected** full Gnomon HIR implementation in OpenFang.
- Gnomon is the sibling breakthrough project; OpenFang is a consumer.
