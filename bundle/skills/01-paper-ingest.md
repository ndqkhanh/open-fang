---
name: paper-ingest
description: Ingest a paper into the SQLite+FTS5 store with structured claim extraction.
---
# Paper Ingest

Take a paper (URL, arXiv ID, or PDF). Extract:

- Metadata (title, authors, venue, date).
- Abstract.
- Structured claim list with `(claim_id, text, supporting_section)`.
- Backlinks (papers this one cites).

Store in `~/.openfang/store.db` (SQLite + FTS5). The store is
append-only; corrections create new rows.

**Telemetry:** emits `openfang.paper.ingested` per paper.
