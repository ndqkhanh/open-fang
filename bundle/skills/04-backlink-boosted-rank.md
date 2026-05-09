---
name: backlink-boosted-rank
description: Rank papers by claim-quality + backlink graph centrality.
---
# Backlink-Boosted Ranking

Default ranking weight:

```
score = 0.4 * claim_quality + 0.3 * tier_pass_rate + 0.3 * backlink_centrality
```

- `claim_quality` — fraction of claims passing tiers 3–5.
- `tier_pass_rate` — average over all five tiers.
- `backlink_centrality` — log-scaled count of papers in the corpus
  that cite this one (capped to bound the long-tail).

A high backlink count without commensurate claim quality is a
warning sign — flagged for the historian + skeptic specialists.
