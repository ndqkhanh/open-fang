---
name: specialist-cohort-9
description: Nine-specialist cohort with pairwise decorrelation.
---
# Nine-Specialist Cohort

Nine sub-personas score papers along their domain axis:

| # | Specialist | What they score |
|---|------------|------------------|
| 1 | architect | system design soundness |
| 2 | benchmarker | benchmark fairness, leakage |
| 3 | theorist | math / theory consistency |
| 4 | ablator | ablation completeness |
| 5 | applier | applicability to practice |
| 6 | curator | corpus fit, replication potential |
| 7 | historian | prior-art coverage |
| 8 | methodologist | experimental design rigor |
| 9 | skeptic | counterclaim, failure modes |

Scores aggregate via *trimmed mean* (drop top + bottom outlier).
Pair-wise agreement monitored; pairs at >85% agreement on
disagreement-traces have one rotated to probation.

**Lyra Agent Teams pattern:**

```python
for spec in COHORT:
    lead.spawn(TeammateSpec(name=spec, subagent=f"openfang-{spec}"))
# K=9 > 5 warn, < 10 block — requires allow_unsafe_token_overage=True.
```
