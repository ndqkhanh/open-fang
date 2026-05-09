---
name: zero-llm-self-wiring
description: Bootstrap the system from scratch without an LLM call.
---
# Zero-LLM Self-Wiring

OpenFang's deterministic bootstrap path: bring the system from
empty to "ready to ingest" without any LLM call. Lets the system
self-test on a target host before the first real query.

**Steps:**

1. Schema migrate `~/.openfang/store.db` (idempotent).
2. Register the nine specialists with default rubrics.
3. Wire the five-tier verifier with stub passers.
4. Schedule the weekly-feed cron under Lyra v3.7 routines.
5. Emit `openfang.bootstrap.ready`.

`LBL-OPENFANG-BOOTSTRAP-DETERMINISTIC` — no LLM call in this path,
ever. Bootstrap correctness must be deterministic across runs.
