"""MulticaAdapter (v5.5) — OpenFang as a multica agent runtime.

multica's protocol (per its README): task-assignment lifecycle
    enqueue → claim → start → progress... → complete | fail

Messages are JSON envelopes; transport is WebSocket in multica's prod
deployment, but this adapter is transport-agnostic — callers provide a
`send(message)` callable. v5.5 MVP uses this hook-based shape so:

    - tests can dispatch sync messages without a real WebSocket server,
    - production can wrap `send` with a WebSocket-send call.

When multica dispatches a new task, the adapter runs it through an
`OpenFangPipeline` and streams progress events via `send`.
"""
from __future__ import annotations

import datetime as _dt
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from ..models import Brief
from ..pipeline import OpenFangPipeline

EventKind = Literal[
    "task_claimed",
    "task_started",
    "task_progress",
    "task_completed",
    "task_failed",
]


@dataclass
class MulticaMessage:
    """One task-assignment envelope from multica."""

    task_id: str
    brief: dict[str, Any]
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class MulticaEvent:
    """Progress/outcome event this adapter emits back to multica."""

    task_id: str
    kind: EventKind
    timestamp: str
    payload: dict[str, Any] = field(default_factory=dict)


class MulticaAdapter:
    """Turns a multica task assignment into an OpenFang pipeline run.

    Emits task_claimed → task_started → task_completed (or task_failed) via
    the user-supplied `send` callable.
    """

    def __init__(
        self,
        *,
        pipeline: OpenFangPipeline,
        send: Callable[[MulticaEvent], None],
        agent_name: str = "open-fang",
    ) -> None:
        self.pipeline = pipeline
        self.send = send
        self.agent_name = agent_name

    def handle(self, message: MulticaMessage) -> MulticaEvent:
        """Process one task-assignment message; returns the terminal event."""
        task_id = message.task_id or uuid.uuid4().hex[:12]
        self._emit(task_id, "task_claimed", {"agent": self.agent_name})
        self._emit(task_id, "task_started", {"agent": self.agent_name})
        try:
            brief = Brief(**_brief_from_payload(message.brief))
            result = self.pipeline.run(brief)
        except Exception as exc:  # noqa: BLE001
            return self._emit(
                task_id,
                "task_failed",
                {
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
        summary = {
            "faithfulness_ratio": result.report.faithfulness_ratio,
            "verified_claims": result.report.verified_claims,
            "total_claims": result.report.total_claims,
            "parked_nodes": result.parked_nodes,
            "failed_nodes": result.failed_nodes,
            "activated_skills": result.activated_skills,
            "markdown": result.report.to_markdown(),
        }
        return self._emit(task_id, "task_completed", summary)

    def _emit(self, task_id: str, kind: EventKind, payload: dict[str, Any]) -> MulticaEvent:
        event = MulticaEvent(
            task_id=task_id,
            kind=kind,
            timestamp=_dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            payload=payload,
        )
        self.send(event)
        return event


def _brief_from_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Narrow + coerce a multica task payload to Brief's init kwargs."""
    return {
        "question": str(raw.get("question", "")),
        "domain": raw.get("domain"),
        "max_cost_usd": float(raw.get("max_cost_usd", 0.50)),
        "min_papers": int(raw.get("min_papers", 3)),
        "require_peer_reviewed": bool(raw.get("require_peer_reviewed", False)),
        "target_length_words": int(raw.get("target_length_words", 1500)),
        "style": str(raw.get("style", "standard")),
    }
