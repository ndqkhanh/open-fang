# OpenFang eval rubric

A trace **passes** when:

1. Paper-ingest produced a structured claim list.
2. The verifier reached its `expected_tier_pass` (per trace).
3. At least 7 of the 9 specialists scored the paper (cohort coverage
   ≥0.78).
4. Backlinks were extracted into the graph store.

Aggregate metrics:

- **Tier-pass distribution** — count of papers by max tier passed.
- **Cohort coverage** — average specialists per paper.
- **Backlink ingest rate** — backlinks per paper average.
- **Reproduction success** — fraction of tier-4 attempts that
  reproduced cleanly.
