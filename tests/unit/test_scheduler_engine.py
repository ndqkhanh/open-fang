from __future__ import annotations

from open_fang.models import Brief
from open_fang.planner.llm_planner import DAGPlanner
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.mock import MockSource


def test_scheduler_walks_dag_end_to_end(canned_evidence):
    dag = DAGPlanner().plan(Brief(question="rewoo vs react"))
    engine = SchedulerEngine(source=MockSource(canned=canned_evidence))
    evidence, parked, failed = engine.run(dag)
    assert parked == []
    assert failed == []
    assert all(n.status in {"done", "parked"} for n in dag.nodes)
    assert len(evidence) >= 1
