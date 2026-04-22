"""ToolOutputSandbox (v7.0, W1).

Clean-room adoption of the Context Mode pattern (github.com/mksglu/context-mode):
when a tool/source adapter returns more than `threshold_bytes`, the full
payload is persisted in SQLite + FTS5 and only the top-k by relevance flow
into pipeline context. The remaining items are BM25-retrievable on demand
via the sandbox handle.

Usage:
    sandbox = ToolOutputSandbox(kb)
    handle, top_k = sandbox.sandbox(
        evidence=search_results,
        source_kind="search.arxiv",
        query="rewoo",
        top_k=5,
    )
    # `top_k` flows into context; full list stored under `handle`.

    # Later, retrieve the missing items:
    relevant = sandbox.retrieve(handle, "token reduction", limit=3)

Threshold is env-configurable via `OPEN_FANG_SANDBOX_THRESHOLD_BYTES`
(default 5000 bytes — matches Context Mode's documented trigger).
"""
from __future__ import annotations

import datetime as _dt
import os
import uuid
from dataclasses import dataclass

from ..kb.store import KBStore
from ..models import Evidence, SourceRef

DEFAULT_THRESHOLD_BYTES = 5000


@dataclass
class SandboxStats:
    total_sandboxed: int = 0
    total_items_stored: int = 0
    total_bytes_deferred: int = 0


def threshold_from_env(default: int = DEFAULT_THRESHOLD_BYTES) -> int:
    raw = os.environ.get("OPEN_FANG_SANDBOX_THRESHOLD_BYTES", "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def payload_size_bytes(evidence: list[Evidence]) -> int:
    """Byte count of the evidence list's content (UTF-8 encoded)."""
    return sum(len((e.content or "").encode("utf-8")) for e in evidence)


class ToolOutputSandbox:
    def __init__(
        self,
        kb: KBStore,
        *,
        threshold_bytes: int | None = None,
    ) -> None:
        self._kb = kb
        self.threshold_bytes = (
            threshold_bytes if threshold_bytes is not None else threshold_from_env()
        )
        self.stats = SandboxStats()

    @property
    def _c(self):  # noqa: ANN201
        return self._kb._c  # noqa: SLF001 — shared connection

    # ---------------------------------------------------------------- sandbox

    def should_sandbox(self, evidence: list[Evidence]) -> bool:
        return payload_size_bytes(evidence) > self.threshold_bytes

    def sandbox(
        self,
        *,
        evidence: list[Evidence],
        source_kind: str,
        query: str,
        top_k: int = 5,
    ) -> tuple[str, list[Evidence]]:
        """Store the full `evidence` list; return (handle, top_k_by_relevance).

        The caller passes `top_k` back into context; the rest stay in SQLite
        and are retrievable via `retrieve(handle, query)`.
        """
        handle = uuid.uuid4().hex[:12]
        now = _dt.datetime.utcnow().isoformat(timespec="seconds")
        for ev in evidence:
            self._c.execute(
                """
                INSERT OR REPLACE INTO sandbox_outputs
                  (handle, evidence_id, source_kind, source_identifier,
                   title, content, channel, relevance, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    handle,
                    ev.id,
                    source_kind,
                    ev.source.identifier,
                    ev.source.title,
                    ev.content or "",
                    ev.channel,
                    float(ev.relevance),
                    now,
                ),
            )
            self._c.execute(
                """
                INSERT INTO sandbox_outputs_fts (handle, evidence_id, title, content)
                VALUES (?, ?, ?, ?)
                """,
                (handle, ev.id, ev.source.title, ev.content or ""),
            )
        self._c.commit()

        self.stats.total_sandboxed += 1
        self.stats.total_items_stored += len(evidence)
        self.stats.total_bytes_deferred += payload_size_bytes(evidence)

        # Rank by explicit relevance, newest first on ties.
        ranked = sorted(evidence, key=lambda e: -float(e.relevance))
        return handle, ranked[:top_k]

    # --------------------------------------------------------------- retrieve

    def retrieve(self, handle: str, query: str, *, limit: int = 5) -> list[Evidence]:
        """BM25 against the sandboxed payload under `handle`."""
        q = _to_fts_query(query)
        if not q:
            return []
        rows = self._c.execute(
            """
            SELECT o.handle, o.evidence_id, o.source_kind, o.source_identifier,
                   o.title, o.content, o.channel, o.relevance
            FROM sandbox_outputs_fts f
            JOIN sandbox_outputs o
              ON o.handle = f.handle AND o.evidence_id = f.evidence_id
            WHERE sandbox_outputs_fts MATCH ? AND f.handle = ?
            ORDER BY rank
            LIMIT ?
            """,
            (q, handle, limit),
        ).fetchall()
        return [_row_to_evidence(r) for r in rows]

    def get_all(self, handle: str) -> list[Evidence]:
        """Fetch every sandboxed item under `handle` (no ranking)."""
        rows = self._c.execute(
            """
            SELECT handle, evidence_id, source_kind, source_identifier,
                   title, content, channel, relevance
            FROM sandbox_outputs WHERE handle = ?
            ORDER BY rowid ASC
            """,
            (handle,),
        ).fetchall()
        return [_row_to_evidence(r) for r in rows]

    def count_under(self, handle: str) -> int:
        row = self._c.execute(
            "SELECT COUNT(*) FROM sandbox_outputs WHERE handle = ?",
            (handle,),
        ).fetchone()
        return int(row[0]) if row else 0


# ----------------------------------------------------------------- helpers


def _to_fts_query(query: str) -> str:
    tokens = [t for t in query.replace("'", "").split() if t]
    if not tokens:
        return ""
    return " OR ".join(f'"{t}"' for t in tokens)


def _row_to_evidence(row) -> Evidence:  # noqa: ANN001 — sqlite3.Row
    return Evidence(
        id=row["evidence_id"],
        source=SourceRef(
            kind=row["source_kind"] or "sandbox",
            identifier=row["source_identifier"] or "",
            title=row["title"] or "",
        ),
        content=row["content"] or "",
        channel=row["channel"] or "body",
        relevance=float(row["relevance"] or 0.0),
    )
