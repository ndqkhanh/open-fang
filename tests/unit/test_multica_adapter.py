from __future__ import annotations

from open_fang.adapters.multica import (
    MulticaAdapter,
    MulticaEvent,
    MulticaMessage,
)
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.mock import MockSource


def _pipeline(canned_evidence):
    return OpenFangPipeline(
        scheduler=SchedulerEngine(source=MockSource(canned=canned_evidence)),
    )


def test_adapter_emits_expected_lifecycle_events(canned_evidence):
    events: list[MulticaEvent] = []
    adapter = MulticaAdapter(pipeline=_pipeline(canned_evidence), send=events.append)
    message = MulticaMessage(
        task_id="task-123",
        brief={"question": "what is rewoo", "target_length_words": 300},
    )
    terminal = adapter.handle(message)

    kinds = [e.kind for e in events]
    assert kinds[0] == "task_claimed"
    assert kinds[1] == "task_started"
    assert kinds[-1] == "task_completed"
    # Terminal event returned matches what was sent.
    assert terminal.kind == "task_completed"
    # Every event carries the same task_id.
    assert all(e.task_id == "task-123" for e in events)
    # Completed event has pipeline summary fields.
    payload = terminal.payload
    assert "faithfulness_ratio" in payload
    assert "verified_claims" in payload
    assert "total_claims" in payload
    assert "markdown" in payload


def test_adapter_generates_task_id_when_missing(canned_evidence):
    events: list[MulticaEvent] = []
    adapter = MulticaAdapter(pipeline=_pipeline(canned_evidence), send=events.append)
    terminal = adapter.handle(
        MulticaMessage(task_id="", brief={"question": "rewoo"})
    )
    assert terminal.task_id  # non-empty generated id
    assert all(e.task_id == terminal.task_id for e in events)


def test_adapter_emits_task_failed_on_exception():
    def _broken_brief_payload(_self):  # noqa: ARG001
        raise RuntimeError("simulated failure")

    # Provide a brief with missing question to trigger ValueError in DAGPlanner.
    events: list[MulticaEvent] = []

    class BrokenPipeline:
        def run(self, brief):  # noqa: ANN001
            raise RuntimeError("simulated downstream failure")

    adapter = MulticaAdapter(
        pipeline=BrokenPipeline(),  # type: ignore[arg-type]
        send=events.append,
    )
    terminal = adapter.handle(
        MulticaMessage(task_id="task-err", brief={"question": "rewoo"})
    )
    assert terminal.kind == "task_failed"
    assert "simulated" in terminal.payload["error"]


def test_adapter_carries_agent_name():
    events: list[MulticaEvent] = []
    adapter = MulticaAdapter(
        pipeline=None,  # type: ignore[arg-type] — not used by this test
        send=events.append,
        agent_name="open-fang-custom",
    )
    adapter._emit("t", "task_claimed", {"agent": "open-fang-custom"})
    assert events[0].payload["agent"] == "open-fang-custom"
