# Block specs

One file per component, filled in during the phase that ships it.

| # | File | Phase | Component |
|---|---|---|---|
| 01 | `01-intake-brief.md` | 1 | Brief intake + validation |
| 02 | `02-dag-planner.md` | 1 | LLM planner → typed DAG |
| 03 | `03-scheduler.md` | 1 | Deterministic walker + parking + retries |
| 04 | `04-source-router.md` | 2 | arxiv / S2 / github dispatch |
| 05 | `05-fetcher-parser.md` | 2 | PDF fetch, LaTeX parse |
| 06 | `06-claim-extractor.md` | 3 | Section → Claim with evidence spans |
| 07 | `07-citation-resolver.md` | 4 | KB citation-graph edges |
| 08 | `08-claim-verifier.md` | 3 | Claim ↔ source evidence span |
| 09 | `09-synthesizer.md` | 3 | Structural claim-evidence binding |
| 10 | `10-critic-loop.md` | 3 | Chain-of-verification |
| 11 | `11-kb-and-graph.md` | 4 | SQLite+FTS5 schema + edges |
| 12 | `12-permission-bridge.md` | 5 | Runtime-enforced risk gate |
| 13 | `13-memory-tiers.md` | 5 | working / retrieval / FANG.md |
| 14 | `14-observability.md` | 1 | Gnomon-shape primitive spans |
| 15 | `15-skill-library.md` | v2 | Hermes/Voyager skill library |
