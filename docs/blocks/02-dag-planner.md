# 02 — DAGPlanner

## Purpose

Turn a user `Brief` + `FANG.md` persona into a typed research DAG.
Phase-1 SemaClaw-shape: the LLM plans, a deterministic scheduler executes.

## Interface

```python
DAGPlanner(llm: LLMProvider | None = None).plan(brief, *, persona=None) -> DAG
```

- When `llm` is wired, the planner asks for a JSON DAG and parses it; on parse
  failure, schema failure, or unknown node kind, it **falls back** to a
  deterministic canonical DAG rather than crashing.
- When `llm` is `None`, the planner always returns the canonical DAG. This is
  the test-default in `tests/conftest.py`.

## LLM JSON contract

```json
{
  "nodes": [
    {"id": "R1", "kind": "kb.lookup", "args": {"query": "..."},
     "depends_on": [], "risk": "low"}
  ],
  "estimated_cost_usd": 0.17
}
```

Allowed kinds: see `NodeKind` in [../../src/open_fang/models.py](../../src/open_fang/models.py).

## Canonical fallback DAG

`R1 kb.lookup → R2 search.arxiv → R3 fetch.pdf → R4 extract.claims → R5 verify.claim → R6 synthesize.briefing`

`R6` fans in from both `R1` and `R5` so KB hits and fresh retrieval are both
available to synthesis.

## Schema validation

Every DAG passes through `planner/schema.py:validate_dag()`:

- unique node IDs
- all `depends_on` resolve to known nodes
- no cycles (DFS with visiting / visited sets)

Failing any check raises `DAGSchemaError`, which the LLM path catches and
treats as "bad plan → fall back to canonical".

## Tests

- [tests/unit/test_planner_schema.py](../../tests/unit/test_planner_schema.py)
- [tests/unit/test_planner_llm.py](../../tests/unit/test_planner_llm.py)

## Open questions / v2

- Replanner with hints (`planner/replanner.py` skeleton) for a second LLM turn
  when the first emits a malformed DAG.
- Persona-aware planning: currently the persona is passed but unused by the
  canonical planner; LLM path embeds it in the user prompt.
