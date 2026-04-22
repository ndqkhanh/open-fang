"""KBStore: SQLite + FTS5 literature knowledge base.

Responsibilities:
    - Initialize schema from kb/schema.sql (idempotent).
    - Upsert papers + claims, keyed on source identifier (arxiv id preferred).
    - Full-text search via FTS5; returns Evidence rows for pipeline consumption.
    - Add citation-graph edges.

v1 uses standalone FTS5 (papers row stored twice, in `papers` and `papers_fts`).
v2 target: external-content FTS with sync triggers.
"""
from __future__ import annotations

import datetime as _dt
import sqlite3
import uuid
from pathlib import Path

from ..models import Evidence, SourceRef

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class KBStore:
    def __init__(self, *, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    def open(self) -> KBStore:
        if self._conn is not None:
            return self
        # check_same_thread=False lets FastAPI's threadpool serve requests off
        # the same connection. Single-writer only for v2; connection pooling
        # is v3.
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        self._conn.commit()
        return self

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> KBStore:
        return self.open()

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def _c(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("KBStore not opened; call .open() first")
        return self._conn

    def upsert_paper(self, source: SourceRef, *, abstract: str) -> str:
        """Idempotent paper insert keyed on source.identifier. Returns paper_id."""
        paper_id = source.identifier
        authors = ",".join(source.authors)
        now = _dt.datetime.utcnow().isoformat(timespec="seconds")
        self._c.execute(
            """
            INSERT INTO papers (id, kind, title, abstract, authors, published_at, first_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                abstract = excluded.abstract,
                authors = excluded.authors,
                published_at = excluded.published_at
            """,
            (paper_id, source.kind, source.title, abstract, authors, source.published_at, now),
        )
        # Keep FTS mirror in sync (standalone table; no triggers in v1).
        self._c.execute("DELETE FROM papers_fts WHERE paper_id = ?", (paper_id,))
        self._c.execute(
            "INSERT INTO papers_fts (paper_id, title, abstract) VALUES (?, ?, ?)",
            (paper_id, source.title, abstract),
        )
        self._c.commit()
        return paper_id

    def add_claim(
        self,
        *,
        paper_id: str,
        text: str,
        channel: str = "body",
        verified: bool = False,
        cross_channel_confirmed: bool = False,
    ) -> str:
        claim_id = uuid.uuid4().hex[:12]
        self._c.execute(
            """
            INSERT INTO claims (id, paper_id, text, channel, verified, cross_channel_confirmed)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (claim_id, paper_id, text, channel, int(verified), int(cross_channel_confirmed)),
        )
        self._c.commit()
        return claim_id

    def add_edge(self, src_paper_id: str, dst_paper_id: str, kind: str) -> None:
        self._c.execute(
            """
            INSERT OR IGNORE INTO edges (src_paper_id, dst_paper_id, kind)
            VALUES (?, ?, ?)
            """,
            (src_paper_id, dst_paper_id, kind),
        )
        self._c.commit()

    def list_edges(self, paper_id: str) -> list[tuple[str, str, str]]:
        rows = self._c.execute(
            "SELECT src_paper_id, dst_paper_id, kind FROM edges WHERE src_paper_id = ? OR dst_paper_id = ?",
            (paper_id, paper_id),
        ).fetchall()
        return [(r["src_paper_id"], r["dst_paper_id"], r["kind"]) for r in rows]

    def count_papers(self) -> int:
        return int(self._c.execute("SELECT COUNT(*) FROM papers").fetchone()[0])

    def count_claims(self) -> int:
        return int(self._c.execute("SELECT COUNT(*) FROM claims").fetchone()[0])

    def get_paper(self, paper_id: str) -> Evidence | None:
        """Fetch a single paper row as an Evidence instance (channel='kb-cache')."""
        row = self._c.execute(
            "SELECT id, kind, title, abstract, authors, published_at FROM papers WHERE id = ?",
            (paper_id,),
        ).fetchone()
        return _row_to_evidence(row) if row is not None else None

    def sample_papers(self, limit: int = 5) -> list[Evidence]:
        """Deterministic sample via ROWID ascending; stable across runs."""
        rows = self._c.execute(
            """
            SELECT id, kind, title, abstract, authors, published_at
            FROM papers ORDER BY rowid ASC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_row_to_evidence(r) for r in rows]

    def list_paper_ids(self) -> list[str]:
        rows = self._c.execute("SELECT id FROM papers ORDER BY rowid ASC").fetchall()
        return [r["id"] for r in rows]

    def list_outgoing_edges(self, paper_id: str) -> list[tuple[str, str]]:
        """Return (dst_paper_id, kind) pairs for outgoing edges from `paper_id`."""
        rows = self._c.execute(
            "SELECT dst_paper_id, kind FROM edges WHERE src_paper_id = ?",
            (paper_id,),
        ).fetchall()
        return [(r["dst_paper_id"], r["kind"]) for r in rows]

    def search(self, query: str, *, limit: int = 5) -> list[Evidence]:
        """FTS5 search over (title, abstract). Returns Evidence with kind='kb'."""
        if not query.strip():
            return []
        match = _to_fts_query(query)
        rows = self._c.execute(
            """
            SELECT p.id, p.kind, p.title, p.abstract, p.authors, p.published_at
            FROM papers_fts f
            JOIN papers p ON p.id = f.paper_id
            WHERE papers_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (match, limit),
        ).fetchall()
        return [_row_to_evidence(r) for r in rows]


def _to_fts_query(query: str) -> str:
    """Sanitize a user query for FTS5 MATCH. Quotes each token; OR joins them."""
    tokens = [t for t in query.replace("'", "").split() if t]
    if not tokens:
        return ""
    quoted = [f'"{t}"' for t in tokens]
    return " OR ".join(quoted)


def _row_to_evidence(row: sqlite3.Row) -> Evidence:
    return Evidence(
        source=SourceRef(
            kind=row["kind"] or "kb",
            identifier=row["id"],
            title=row["title"] or "",
            authors=(row["authors"] or "").split(",") if row["authors"] else [],
            published_at=row["published_at"],
        ),
        content=row["abstract"] or "",
        channel="kb-cache",
        relevance=1.0,
    )
