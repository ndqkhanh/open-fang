from __future__ import annotations

from open_fang.models import Brief
from open_fang.planner.llm_planner import DAGPlanner
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.scheduler.parking import ParkingRegistry
from open_fang.sources.mock import MockSource


def test_parked_node_does_not_block_siblings(canned_evidence):
    dag = DAGPlanner().plan(Brief(question="rewoo"))
    parking = ParkingRegistry()
    parking.park("R2")  # force arxiv search to park
    engine = SchedulerEngine(
        source=MockSource(canned=canned_evidence),
        parking=parking,
    )
    _, parked, failed = engine.run(dag)
    assert "R2" in parked
    assert failed == []
    # Sibling R1 (kb.lookup) must still run
    r1 = next(n for n in dag.nodes if n.id == "R1")
    assert r1.status == "done"
