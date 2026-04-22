from __future__ import annotations

from open_fang.models import DAG, Node
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.mock import MockSource
from open_fang.supervisor.isolated import (
    IsolatedSupervisor,
    IsolatedSupervisorConfig,
    isolated_mode_enabled,
)
from open_fang.supervisor.specialist import (
    ClaimVerifierAgent,
    CriticAgent,
    DeepReadAgent,
    MethodologistAgent,
    PublisherAgent,
    ResearchDirectorAgent,
    SurveyAgent,
    SynthesisAgent,
    ThreatModelerAgent,
)


def test_isolated_mode_flag_respects_env(monkeypatch):
    monkeypatch.setenv("OPEN_FANG_SUPERVISOR_MODE", "isolated")
    assert isolated_mode_enabled() is True
    monkeypatch.setenv("OPEN_FANG_SUPERVISOR_MODE", "asyncio")
    assert isolated_mode_enabled() is False
    monkeypatch.delenv("OPEN_FANG_SUPERVISOR_MODE", raising=False)
    assert isolated_mode_enabled() is False


def test_isolated_supervisor_dispatches_through_subprocess(canned_evidence):
    """A minimal subprocess round-trip validates the isolation pathway."""
    isolated = IsolatedSupervisor(
        specialists=[SurveyAgent()],
        config=IsolatedSupervisorConfig(timeout_s=10.0),
    )
    scheduler = SchedulerEngine(
        source=MockSource(canned=canned_evidence),
        supervisor=isolated,
    )
    dag = DAG(nodes=[Node(id="A", kind="search.arxiv", args={"query": "rewoo"})])
    evidence, parked, failed = scheduler.run(dag)
    assert failed == []
    assert parked == []
    assert dag.nodes[0].status == "done"
    # Supervisor stats reflect the subprocess dispatch.
    assert isolated.stats.per_specialist["survey"].dispatched == 1
    assert isolated.stats.per_specialist["survey"].errors == 0


def test_isolated_supervisor_falls_through_on_unclaimed_kind():
    """Unclaimed kinds use the scheduler's default handler; supervisor is silent."""
    isolated = IsolatedSupervisor(
        specialists=[
            ResearchDirectorAgent(),
            SurveyAgent(),
            DeepReadAgent(),
            ClaimVerifierAgent(),
            MethodologistAgent(),
            SynthesisAgent(),
            CriticAgent(),
            ThreatModelerAgent(),
            PublisherAgent(),
        ]
    )
    scheduler = SchedulerEngine(source=MockSource(), supervisor=isolated)
    # kb.lookup is not claimed by any v4.0 specialist.
    dag = DAG(nodes=[Node(id="L", kind="kb.lookup", args={"query": "x"})])
    _, _, failed = scheduler.run(dag)
    assert failed == []
    # Supervisor was not called because kb.lookup isn't in any handles set.
    assert "survey" not in isolated.stats.per_specialist


def test_span_model_has_stage_field():
    """v4.4 stage labels."""
    from open_fang.models import Span

    span = Span(
        trace_id="t",
        node_id="n",
        kind="search.arxiv",
        started_at=0.0,
        ended_at=0.1,
        stage="retrieve",
    )
    assert span.stage == "retrieve"
    # Stage defaults to None when omitted.
    span2 = Span(
        trace_id="t",
        node_id="n",
        kind="search.arxiv",
        started_at=0.0,
        ended_at=0.1,
    )
    assert span2.stage is None
