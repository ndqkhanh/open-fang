"""MemoryStore: progressive-disclosure observation log (v3.1).

Three tiers per v3-plan.md §3.W2:
    Tier A  compact_index(limit)        — always-in-context one-liners
    Tier B  timeline(offset, limit)     — paginated paragraph summaries
    Tier C  get_observation(id)         — raw span + metadata

Inspired by thedotmack/claude-mem's progressive-disclosure pattern (~10×
token savings claimed). OpenFang's implementation is clean-room: we read
claude-mem's architecture diagram and README only; no code is ported.

Storage: the KB's SQLite file. A dedicated `observations` table is created
by kb/schema.sql (v3.1 addition). MemoryStore takes a `KBStore` in its
constructor so both share the same SQLite connection.
"""
from __future__ import annotations

import datetime as _dt
import json
import uuid
from dataclasses import dataclass
from typing import Any

from ..kb.store import KBStore
from ..models import Span


@dataclass
class Observation:
    id: str
    trace_id: str
    node_id: str
    node_kind: str
    stage: str | None
    verdict: str
    timestamp: str
    compact_summary: str
    detail_summary: str
    full_json: dict[str, Any]


class MemoryStore:
    def __init__(self, kb: KBStore) -> None:
        self._kb = kb

    @property
    def _c(self):  # noqa: ANN201
        return self._kb._c  # noqa: SLF001 — intentional shared connection

    # -------- append --------

    def append(
        self,
        span: Span,
        *,
        stage: str | None = None,
        detail: str | None = None,
    ) -> str:
        """Record a pipeline span as a three-tier observation. Returns the id."""
        obs_id = uuid.uuid4().hex[:12]
        timestamp = _dt.datetime.utcnow().isoformat(timespec="seconds")
        compact = _compact_line(span, timestamp)
        detail_text = detail or _detail_paragraph(span, timestamp)
        full_json = json.dumps(_serialize_span(span, timestamp, stage), separators=(",", ":"))
        self._c.execute(
            """
            INSERT INTO observations
              (id, trace_id, node_id, node_kind, stage, verdict, timestamp,
               compact_summary, detail_summary, full_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obs_id,
                span.trace_id,
                span.node_id,
                span.kind,
                stage,
                span.verdict,
                timestamp,
                compact,
                detail_text,
                full_json,
            ),
        )
        self._c.commit()
        return obs_id

    # -------- retrieval tiers --------

    def compact_index(self, *, limit: int = 20) -> list[str]:
        """Tier A — always-in-context one-liners. Newest first."""
        rows = self._c.execute(
            "SELECT compact_summary FROM observations ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [r["compact_summary"] for r in rows]

    def timeline(self, *, offset: int = 0, limit: int = 20) -> list[Observation]:
        """Tier B — paginated summaries for the timeline endpoint."""
        rows = self._c.execute(
            """
            SELECT id, trace_id, node_id, node_kind, stage, verdict, timestamp,
                   compact_summary, detail_summary
            FROM observations
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [
            Observation(
                id=r["id"],
                trace_id=r["trace_id"],
                node_id=r["node_id"],
                node_kind=r["node_kind"],
                stage=r["stage"],
                verdict=r["verdict"],
                timestamp=r["timestamp"],
                compact_summary=r["compact_summary"],
                detail_summary=r["detail_summary"] or "",
                full_json={},
            )
            for r in rows
        ]

    def get_observation(self, observation_id: str) -> Observation | None:
        """Tier C — full details for one observation, including raw span JSON."""
        row = self._c.execute(
            """
            SELECT id, trace_id, node_id, node_kind, stage, verdict, timestamp,
                   compact_summary, detail_summary, full_json
            FROM observations WHERE id = ?
            """,
            (observation_id,),
        ).fetchone()
        if row is None:
            return None
        return Observation(
            id=row["id"],
            trace_id=row["trace_id"],
            node_id=row["node_id"],
            node_kind=row["node_kind"],
            stage=row["stage"],
            verdict=row["verdict"],
            timestamp=row["timestamp"],
            compact_summary=row["compact_summary"],
            detail_summary=row["detail_summary"] or "",
            full_json=json.loads(row["full_json"] or "{}"),
        )

    def count(self) -> int:
        return int(self._c.execute("SELECT COUNT(*) FROM observations").fetchone()[0])


def _compact_line(span: Span, timestamp: str) -> str:
    return f"[{timestamp}] {span.kind:<20} verdict={span.verdict}"


def _detail_paragraph(span: Span, timestamp: str) -> str:
    parts = [
        f"at {timestamp}",
        f"node_id={span.node_id}",
        f"kind={span.kind}",
        f"verdict={span.verdict}",
    ]
    if span.error:
        parts.append(f"error={span.error}")
    if span.cost_usd:
        parts.append(f"cost=${span.cost_usd:.4f}")
    return " · ".join(parts)


def _serialize_span(span: Span, timestamp: str, stage: str | None) -> dict[str, Any]:
    return {
        "trace_id": span.trace_id,
        "node_id": span.node_id,
        "kind": span.kind,
        "stage": stage,
        "verdict": span.verdict,
        "started_at": span.started_at,
        "ended_at": span.ended_at,
        "cost_usd": span.cost_usd,
        "error": span.error,
        "timestamp": timestamp,
    }
