from __future__ import annotations

from open_fang.models import DAG, Node
from open_fang.permissions.bridge import PermissionBridge
from open_fang.permissions.tokens import TokenRegistry
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.mock import MockSource


def _dag(risk: str = "medium") -> DAG:
    return DAG(
        nodes=[
            Node(id="low", kind="search.arxiv", args={"query": "x"}, risk="low"),
            Node(id="gated", kind="search.github", args={"query": "x"}, risk=risk),
        ]
    )


def test_medium_risk_node_parks_without_token():
    bridge = PermissionBridge(tokens=TokenRegistry())
    engine = SchedulerEngine(source=MockSource(), permission_bridge=bridge)
    dag = _dag(risk="medium")

    _, parked, failed = engine.run(dag)

    assert parked == ["gated"]
    assert failed == []
    assert next(n for n in dag.nodes if n.id == "low").status == "done"
    assert next(n for n in dag.nodes if n.id == "gated").status == "parked"


def test_high_risk_node_denied_without_token():
    bridge = PermissionBridge(tokens=TokenRegistry())
    engine = SchedulerEngine(source=MockSource(), permission_bridge=bridge)
    dag = _dag(risk="high")

    _, parked, failed = engine.run(dag)

    assert failed == ["gated"]
    gated = next(n for n in dag.nodes if n.id == "gated")
    assert gated.status == "failed"
    assert "permission denied" in (gated.error or "")


def test_medium_risk_node_runs_with_session_token():
    tokens = TokenRegistry()
    tokens.grant("search.github", kind="session")
    bridge = PermissionBridge(tokens=tokens)
    engine = SchedulerEngine(source=MockSource(), permission_bridge=bridge)
    dag = _dag(risk="medium")

    _, parked, failed = engine.run(dag)

    assert parked == []
    assert failed == []
    assert next(n for n in dag.nodes if n.id == "gated").status == "done"


def test_low_risk_never_consults_bridge():
    """Bridge isn't called for low-risk nodes even when it would deny."""

    class DenyAllBridge:
        def check(self, *, op: str, risk: str) -> str:  # noqa: ARG002
            return "deny"

    engine = SchedulerEngine(source=MockSource(), permission_bridge=DenyAllBridge())
    dag = DAG(nodes=[Node(id="L", kind="search.arxiv", args={"query": "x"}, risk="low")])
    _, parked, failed = engine.run(dag)
    assert failed == [] and parked == []
    assert next(n for n in dag.nodes if n.id == "L").status == "done"
