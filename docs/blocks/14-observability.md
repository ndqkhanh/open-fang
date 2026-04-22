# 14 — Observability (Gnomon-shape spans)

## Purpose

Every executed DAG node emits a structured span so a failing run can be
attributed to **the specific primitive** that caused the failure — not just
"the trace failed". This is the telemetry floor; it's also the hook that v2
will use for skill extraction (plan.md §3.6, docs/67).

## Span schema

See `Span` in [../../src/open_fang/models.py](../../src/open_fang/models.py):

| Field | Purpose |
|---|---|
| `trace_id` | Correlates every span within one pipeline run |
| `node_id` | Unique within the DAG |
| `kind` | `NodeKind` — tells you the primitive |
| `started_at` / `ended_at` | `time.monotonic()` floats |
| `verdict` | `ok` \| `error` \| `parked` \| `skipped` |
| `error` | Exception message when `verdict="error"` |

## SpanRecorder

`observe/tracer.py:SpanRecorder` holds the in-memory span list for one run.
Called by the scheduler at each node boundary:

```python
rec.record_ok(node, start)
rec.record_error(node, start, exc)
rec.record_parked(node, start)
```

Access `rec.spans` after a run to inspect every primitive that fired.

## Harness-core tracer integration

The pipeline wraps each phase (plan / schedule / synthesize / verify /
critique / kb.promote) in a `harness_core.observability.Tracer.span(...)`
context manager so external tools that consume harness-core traces also see
OpenFang activity.

## Consumers

- Vertex-Eval (sibling project) ingests these spans and produces Pass@k /
  Pass^k + failure-attribution reports.
- Local dev: logs stream to stdout as JSON.

## Tests

- [tests/unit/test_observe_spans.py](../../tests/unit/test_observe_spans.py)

## v2

Attach `cost_usd` per span (needs LLM call-accounting hooked in) and
populate `inputs_preview` / `outputs_preview` for non-sensitive nodes.
