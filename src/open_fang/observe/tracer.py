"""SpanRecorder: collects Gnomon-shape spans during a pipeline run."""
from __future__ import annotations

import time

from ..models import Node, Span
from .spans import make_span, new_trace_id


class SpanRecorder:
    def __init__(self, *, trace_id: str | None = None) -> None:
        self.trace_id = trace_id or new_trace_id()
        self.spans: list[Span] = []

    def record_ok(self, node: Node, started_at: float) -> None:
        self.spans.append(
            make_span(self.trace_id, node, started_at=started_at, ended_at=time.monotonic())
        )

    def record_error(self, node: Node, started_at: float, exc: BaseException) -> None:
        self.spans.append(
            make_span(
                self.trace_id,
                node,
                started_at=started_at,
                ended_at=time.monotonic(),
                verdict="error",
                error=str(exc),
            )
        )

    def record_parked(self, node: Node, started_at: float) -> None:
        self.spans.append(
            make_span(
                self.trace_id,
                node,
                started_at=started_at,
                ended_at=time.monotonic(),
                verdict="parked",
            )
        )
