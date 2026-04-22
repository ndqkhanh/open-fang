# 03 — SchedulerEngine

## Purpose

Phase-2 deterministic walker. Given a typed DAG, execute nodes when their
dependencies are `done`, parallelize independent branches, retry node-locally
on transient failure, park when a permission is missing, fail otherwise.

## Interface

```python
SchedulerEngine(
    source: SourceRouter | SearchSource | None,
    parking: ParkingRegistry | None,
    retry_policy: RetryPolicy | None,
    kb: KBStore | None,
    permission_bridge: PermissionBridge | None,
).run(dag, *, recorder) -> (evidence, parked, failed)
```

## Node lifecycle

```
pending → (dep not ready)  → pending
        → (explicitly parked) → parked  (ParkingRegistry)
        → (bridge verdict park) → parked  (PermissionBridge, risk>low)
        → (bridge verdict deny) → failed  ("permission denied")
        → (handler ok)        → done
        → (handler raised N×) → failed
```

## Dispatch table

| Node kind | Handler |
|---|---|
| `search.arxiv` / `search.semantic_scholar` / `search.github` | `SourceRouter.search(kind, query)` |
| `kb.lookup` | `KBStore.search(query, limit)` |
| everything else | no-op (returns `[]`) |

Non-search / non-KB nodes are pipeline-level: `SynthesisWriter`, `ClaimVerifier`,
`CriticAgent`, and KB promotion all run after scheduler completion on the
accumulated evidence set.

## Retry

`RetryPolicy(max_attempts=3, base_delay_s=0.5, factor=2.0)` is node-local:
the scheduler catches exceptions from `_execute`, sleeps per
`delay_for_attempt(attempt)`, and retries. Tests set `base_delay_s=0.0`.

## Parking vs. failure — fault locality

Parking is *not* failure: siblings continue, the report is produced with a
gap note, and a subsequent run can unblock the gate by granting a token via
`POST /v1/permissions/approve`.

## Tests

- Core walker + happy path: [tests/unit/test_scheduler_engine.py](../../tests/unit/test_scheduler_engine.py)
- Parking: [tests/unit/test_scheduler_parking.py](../../tests/unit/test_scheduler_parking.py)
- Retry: [tests/integration/test_pipeline_retry.py](../../tests/integration/test_pipeline_retry.py)
- Permissions: [tests/unit/test_scheduler_permissions.py](../../tests/unit/test_scheduler_permissions.py)
