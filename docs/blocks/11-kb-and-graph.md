# 11 — KB and citation graph

## Purpose

Literature knowledge base: a local SQLite + FTS5 store that accumulates
every verified claim + its source paper across sessions. Feeds the
`kb.lookup` node so a second run on the same topic can avoid re-fetching.

## Tables

```
papers(id, kind, title, abstract, authors, published_at, first_seen_at)
claims(id, paper_id, text, channel, verified, cross_channel_confirmed)
edges(src_paper_id, dst_paper_id, kind)
papers_fts — FTS5 mirror of (title, abstract)
```

`papers.id` is the source identifier (`arxiv:2305.18323`, `s2:xyz`, or a
github URL). Upsert uses `INSERT … ON CONFLICT(id) DO UPDATE` so re-ingesting
a known paper is idempotent.

## Edge kinds

`cites | extends | refutes | shares-author | same-benchmark | same-technique-family`

v1 doesn't auto-populate edges — citation extraction from PDFs is Phase v2.
Edges can be added programmatically via `KBStore.add_edge(src, dst, kind)`.

## FTS search

```python
kb.search("rewoo reasoning", limit=5) -> list[Evidence]
```

Each hit returns `Evidence(channel="kb-cache", source.kind=... , relevance=1.0)`.
Query tokens are single-quoted into FTS5 `MATCH` expressions (apostrophes
safely stripped; see `_to_fts_query`).

## Promotion gate

`kb.promote.promote_report(report, evidence, kb)` walks verified claims,
upserts source papers (deduped across claims), and records claims linked to
papers. Skipped: unverified, no-anchor. Returns a `PromotionReport`.

The pipeline runs promotion automatically when `OpenFangPipeline(kb=...)` is
wired; in the HTTP surface, the default pipeline ships without a KB, and a
future per-session KB route will be added in v1.1.

## v1 vs. v2 schema

v1 uses **standalone** FTS5 (papers row stored twice — redundant but
trigger-free). v2 target is `content='papers'` external-content FTS with
insert/update/delete sync triggers. Schema source of truth:
[../../src/open_fang/kb/schema.sql](../../src/open_fang/kb/schema.sql).

## Container persistence

The v1 `Containerfile` sets `OPEN_FANG_DB_PATH=/data/open_fang.db` and
`docker-compose.yml` mounts the `open-fang-kb` named volume at `/data`, so
the KB survives container restarts.

## Tests

- [tests/unit/test_kb_store.py](../../tests/unit/test_kb_store.py)
- [tests/unit/test_kb_promote_report.py](../../tests/unit/test_kb_promote_report.py)
- [tests/integration/test_kb_two_runs.py](../../tests/integration/test_kb_two_runs.py)
