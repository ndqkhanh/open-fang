# OpenFang — System Design

## API surface (v1)

```
POST /v1/research                Brief → Report
GET  /v1/kb/papers               list                           (Phase 4)
GET  /v1/kb/paper/{id}           detail + citation edges        (Phase 4)
GET  /v1/kb/graph                citation subgraph              (Phase 4)
POST /v1/permissions/approve     grant session/once/pattern tok (Phase 5)
GET  /healthz                    {"status":"ok","service":"open-fang"}
```

### `Brief`

| Field | Type | Default | Notes |
|---|---|---|---|
| `question` | string | required | research question |
| `domain` | string\|null | infer from FANG.md | |
| `max_cost_usd` | float | 0.50 | enforced by cost_router |
| `min_papers` | int | 3 | planner lower bound |
| `require_peer_reviewed` | bool | false | |
| `target_length_words` | int | 1500 | |
| `style` | string | "standard" | terse \| standard \| exhaustive |

### `Report`

See `src/open_fang/models.py` for the full schema. Notable fields:

- `sections[*].claims[*].evidence_ids` — structural binding to `references`.
- `faithfulness_ratio`, `verified_claims`, `total_claims`.
- `cost_usd`, `dag_id`, `trace_id`.

## Deployment

- `make docker-up` → container on `:8010`.
- Healthcheck polls `/healthz` every 30s.
- Env: `ANTHROPIC_API_KEY`, `HARNESS_LLM_MODEL`, `ARXIV_EMAIL`, `S2_API_KEY`.

## SLOs (target, not measured)

| Metric | Target |
|---|---|
| `faithfulness_ratio` (per brief) | ≥ 0.90 |
| Pass^5 on 20-brief eval set | ≥ 0.70 |
| `cost_usd` per brief | ≤ `$0.50` |
| p95 latency per brief | ≤ 120s |

## Operational notes

- All LLM calls go through `harness_core.models`; `MockLLM` in tests.
- KB is SQLite file at `OPEN_FANG_DB_PATH`; treat as ephemeral in CI, persistent in prod.
- Spans emit to stdout as JSON; pipe to your log aggregator.
