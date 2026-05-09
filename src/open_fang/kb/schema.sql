-- OpenFang literature KB schema (SQLite + FTS5).
-- v1: standalone FTS5 mirror of papers (redundant storage, simpler sync).
-- v2: switch to `content='papers'` external-content FTS with triggers.

CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,         -- 'arxiv' | 's2' | 'github' | 'kb'
    title TEXT NOT NULL,
    abstract TEXT NOT NULL,
    authors TEXT NOT NULL,      -- comma-joined
    published_at TEXT,
    first_seen_at TEXT NOT NULL -- ISO timestamp
);

CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(id),
    text TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'body',
    verified INTEGER NOT NULL DEFAULT 0,
    cross_channel_confirmed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS edges (
    src_paper_id TEXT NOT NULL REFERENCES papers(id),
    dst_paper_id TEXT NOT NULL REFERENCES papers(id),
    kind TEXT NOT NULL,         -- cites | extends | refutes | shares-author | same-benchmark | same-technique-family
    PRIMARY KEY (src_paper_id, dst_paper_id, kind)
);

CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
    paper_id UNINDEXED,
    title,
    abstract
);

-- v7.1: dense-embedding sidecar for papers. Populated lazily — rows can be
-- missing until an Embedder runs over a paper. HybridSearch tolerates the
-- gap by falling through to BM25 when no embeddings exist.
CREATE TABLE IF NOT EXISTS papers_embeddings (
    paper_id TEXT PRIMARY KEY REFERENCES papers(id),
    embedding BLOB NOT NULL,
    dim INTEGER NOT NULL,
    model_id TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_claims_paper_id ON claims(paper_id);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src_paper_id);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_paper_id);

-- v7.0: tool-output sandbox (Context Mode pattern).
-- When a source adapter returns > threshold bytes, the full payload is stored
-- here and only the top-k matches flow into pipeline context. Retrieve the
-- rest via the sandbox handle + BM25 query.
CREATE TABLE IF NOT EXISTS sandbox_outputs (
    handle TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    source_kind TEXT,
    source_identifier TEXT,
    title TEXT,
    content TEXT NOT NULL,
    channel TEXT,
    relevance REAL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (handle, evidence_id)
);
CREATE INDEX IF NOT EXISTS idx_sandbox_handle ON sandbox_outputs(handle);
CREATE VIRTUAL TABLE IF NOT EXISTS sandbox_outputs_fts USING fts5(
    handle UNINDEXED,
    evidence_id UNINDEXED,
    title,
    content
);

-- v3.1: progressive-disclosure observations log.
-- Each row captures one pipeline span across three disclosure tiers:
--   compact_summary  → Tier A (always-in-context; one-liner, ~50-100 tokens)
--   detail_summary   → Tier B (timeline endpoint; paragraph)
--   full_json        → Tier C (per-id endpoint; raw span + metadata)
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    node_kind TEXT NOT NULL,
    stage TEXT,                 -- v4 lifecycle stage; nullable until v4 lands
    verdict TEXT NOT NULL,      -- 'ok' | 'error' | 'parked' | 'skipped'
    timestamp TEXT NOT NULL,    -- ISO-8601 UTC
    compact_summary TEXT NOT NULL,
    detail_summary TEXT,
    full_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_obs_trace ON observations(trace_id);
CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(timestamp);
