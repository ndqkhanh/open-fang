# OpenFang seed memory

## Default cohort roster

The nine specialists ship with default rubrics in
`~/.openfang/cohort/`:

- `architect` — design soundness, modularity, interface clarity.
- `benchmarker` — benchmark fairness, leakage, reproducibility.
- `theorist` — math, theorem consistency, proof gaps.
- `ablator` — ablation completeness, control sufficiency.
- `applier` — practical applicability, rollout cost.
- `curator` — corpus fit, replication potential.
- `historian` — prior-art coverage, novelty claims.
- `methodologist` — experimental design rigor.
- `skeptic` — counterclaim coverage, failure modes.

## Default tier thresholds

- Tier 1 (parse): pass = no syntactic errors.
- Tier 2 (cite): pass = ≥95% citations correct.
- Tier 3 (ground): pass = ≥80% claims survive re-derivation.
- Tier 4 (reproduce): pass = ≥70% experimental claims reproduce.
- Tier 5 (meta): pass = ≥90% claims consistent with corpus.

## Default backfill policy

A missed weekly-feed cron triggers a backfill within 24h. Two
consecutive missed runs page the curator (`LBL-OPENFANG-WEEKLY-FEED`).
