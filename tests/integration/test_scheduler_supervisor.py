"""v3.2 exit: scheduler dispatches through the 5-specialist supervisor;
crashing specialist isolated (failure shown on the failing node, siblings succeed).
"""
from __future__ import annotations

from open_fang.models import DAG, Brief, Node
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.mock import MockSource
from open_fang.supervisor.registry import Supervisor, default_supervisor
from open_fang.supervisor.specialist import Specialist, SpecialistContext


def _fixed_dag_brief() -> Brief:
    return Brief(question="what is rewoo")


def test_pipeline_with_default_supervisor_runs_end_to_end(canned_evidence):
    """5-specialist dispatch: the default supervisor claims search/extract/verify/synth/critic
    kinds; the scheduler still completes the pipeline end-to-end."""
    scheduler = SchedulerEngine(
        source=MockSource(canned=canned_evidence),
        supervisor=default_supervisor(),
    )
    pipeline = OpenFangPipeline(scheduler=scheduler)
    result = pipeline.run(_fixed_dag_brief())

    assert result.failed_nodes == []
    assert result.report.total_claims >= 1
    assert result.report.faithfulness_ratio >= 0.5

    # The supervisor recorded at least one dispatch (survey on a search.* node).
    survey_stat = scheduler.supervisor.stats.per_specialist.get("survey")
    assert survey_stat is not None
    assert survey_stat.dispatched >= 1
    assert survey_stat.errors == 0


def test_crashing_specialist_isolated_to_its_nodes(canned_evidence):
    """A specialist that raises on one kind should fail only that node; other
    node kinds (handled by other specialists or scheduler defaults) still run."""

    class CrashingSurvey(Specialist):
        name = "crashing-survey"
        stage = "retrieve"
        handles = {"search.arxiv"}

        def execute(self, node: Node, context: SpecialistContext):  # noqa: ARG002
            raise RuntimeError("intentional crash in test")

    from open_fang.supervisor.specialist import (
        ClaimVerifierAgent,
        CriticAgent,
        DeepReadAgent,
        SynthesisAgent,
    )

    supervisor = Supervisor(
        specialists=[
            CrashingSurvey(),
            DeepReadAgent(),
            ClaimVerifierAgent(),
            SynthesisAgent(),
            CriticAgent(),
        ]
    )
    scheduler = SchedulerEngine(
        source=MockSource(canned=canned_evidence),
        supervisor=supervisor,
    )
    # Single-node DAG running just search.arxiv — the crashing specialist
    # will fail, but the pipeline itself must return cleanly.
    dag = DAG(nodes=[Node(id="A", kind="search.arxiv", args={"query": "q"})])
    evidence, parked, failed = scheduler.run(dag)
    assert "A" in failed
    assert "intentional crash" in (dag.nodes[0].error or "")
    # The supervisor also recorded the error. Scheduler retries call the
    # supervisor once per attempt, so errors ≥ 1 (default max_attempts=3).
    stat = supervisor.stats.per_specialist["crashing-survey"]
    assert stat.errors >= 1
    assert stat.dispatched == stat.errors  # every dispatch for this crashing specialist errors


def test_scheduler_without_supervisor_still_works(canned_evidence):
    """Back-compat: no supervisor → scheduler uses its default handlers."""
    scheduler = SchedulerEngine(source=MockSource(canned=canned_evidence))
    result = OpenFangPipeline(scheduler=scheduler).run(_fixed_dag_brief())
    assert result.failed_nodes == []
    assert result.report.total_claims >= 1


def test_supervisor_does_not_intercept_unclaimed_kind(canned_evidence):
    """`kb.lookup` is not claimed by any default specialist, so the scheduler's
    default handler must still run even when a supervisor is wired."""
    from open_fang.kb.store import KBStore
    from open_fang.models import SourceRef

    kb = KBStore(db_path=":memory:").open()
    kb.upsert_paper(SourceRef(kind="arxiv", identifier="arxiv:x", title="x"), abstract="ReWOO")
    scheduler = SchedulerEngine(
        source=MockSource(canned=canned_evidence),
        kb=kb,
        supervisor=default_supervisor(),
    )
    dag = DAG(nodes=[Node(id="L", kind="kb.lookup", args={"query": "rewoo"})])
    evidence, parked, failed = scheduler.run(dag)
    assert failed == []
    # KB lookup handled by the scheduler's default path.
    assert dag.nodes[0].status == "done"
