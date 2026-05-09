# OpenFang — May-2026 Upgrade Stub

> Companion to [`../CROSS_PROJECT_UPGRADE_PLAN_2026.md`](../CROSS_PROJECT_UPGRADE_PLAN_2026.md).
> Per the cross-project matrix, OpenFang is **W2** — already
> production-quality (612 tests, TDD-first); bundle exposes the
> 5-tier verifier and 9-specialist cohort to Lyra Agent Teams.

## Headline gap (vs 2026 SOTA)

- **No `bundle/`** — paper ingest + 5-tier verifier + 9-specialist
  cohort + chaos hooks not packaged.
- **Weekly-feed cron not Lyra routine** — OpenFang has its own
  scheduler; Lyra v3.7 L37-8 routines could schedule it instead so
  weekly drops feed Lyra's auto-memory directly.
- **5-tier verifier underused** — OpenFang's verifier is the
  highest-density verifier in the portfolio; should feed L311-6
  research-domain coverage as a *separate domain* from Atlas-Research's
  citation-verifier.

## Smallest upgrade

```text
open-fang/bundle/
├── bundle.yaml
├── persona.md
├── skills/
│   ├── 01-paper-ingest.md
│   ├── 02-verifier-5tier.md
│   ├── 03-specialist-cohort-9.md
│   ├── 04-backlink-boosted-rank.md
│   ├── 05-chaos-hooks.md
│   └── 06-zero-llm-self-wiring.md
├── tools/
│   └── mcp_server.py          # SQLite+FTS5 store + verifier + cohort
├── memory/
│   └── seed.md                # default specialist roster
├── evals/
│   ├── golden.jsonl           # BrainBench probes
│   └── rubric.md
└── verifier/
    └── checker.py             # delegates to OpenFang's existing 5-tier
```

## Lyra routine declaration

```yaml
# bundle.yaml — appended
routines:
  - kind: cron
    name: open-fang-weekly-feed
    schedule: "0 9 * * MON"     # 9am Monday
    handler: skills/01-paper-ingest.md
  - kind: webhook
    name: open-fang-on-paper-event
    handler: skills/01-paper-ingest.md
```

## Lyra Agent Teams pattern (9-spoke specialist cohort)

```python
# Spawn 9 specialists in parallel for a paper review.
for spec in OPENFANG_SPECIALISTS:
    lead.spawn(TeammateSpec(name=spec, subagent=f"openfang-{spec}"))

lead.add_task("Review paper X for novelty / methodology / ...",
              # No assign — each specialist claims its domain.
              )
```

This requires `allow_unsafe_token_overage=True` (K=9 > 5 warn,
< 10 block).

## Test plan

- 8+ tests covering bundle validation, routine registration, 9-spoke
  spawn under cost guard, and BrainBench rubric integration.

## Sequencing

W2 — depends on Lyra v3.7 L37-8 + v3.11 L311-1 + L311-4.

## Related Lyra phases

- L37-8 Routines — weekly-feed cron registration.
- L311-1 Agent Teams runtime — 9-spoke specialist cohort.
- L311-6 Verifier coverage — OpenFang's 5-tier feeds research domain.
