"""Gnomon-shape span factory helpers."""
from __future__ import annotations

import time
import uuid

from ..models import Node, Span


def make_span(
    trace_id: str,
    node: Node,
    *,
    started_at: float,
    ended_at: float | None = None,
    verdict: str = "ok",
    error: str | None = None,
) -> Span:
    return Span(
        trace_id=trace_id,
        node_id=node.id,
        kind=node.kind,
        started_at=started_at,
        ended_at=ended_at if ended_at is not None else time.monotonic(),
        verdict=verdict,  # type: ignore[arg-type]
        error=error,
    )


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]
