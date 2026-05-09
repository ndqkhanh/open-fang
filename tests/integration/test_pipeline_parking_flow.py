"""Full parking-then-approve flow via the pipeline (not the HTTP surface).

Setup: a DAG with one high-risk node. First run parks (or fails); after
granting a token on the shared registry, a second pipeline run allows the
same node kind to proceed.
"""
from __future__ import annotations

from open_fang.models import DAG, Brief, Node
from open_fang.permissions.bridge import PermissionBridge
from open_fang.permissions.tokens import TokenRegistry
from open_fang.pipeline import OpenFangPipeline
from open_fang.planner.llm_planner import DAGPlanner
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.mock import MockSource


class _FixedPlanner(DAGPlanner):
    """Emits a tiny DAG with one high-risk node so the flow is deterministic."""

    def __init__(self, risk: str = "medium") -> None:
        super().__init__()
        self.risk = risk

    def plan(self, brief: Brief, *, persona: str | None = None) -> DAG:  # noqa: ARG002
        return DAG(
            nodes=[
                Node(id="search", kind="search.arxiv", args={"query": brief.question}, risk="low"),
                Node(
                    id="gated",
                    kind="search.github",
                    args={"query": brief.question},
                    risk=self.risk,
                ),
            ]
        )


def _build_pipeline(bridge: PermissionBridge) -> OpenFangPipeline:
    scheduler = SchedulerEngine(source=MockSource(), permission_bridge=bridge)
    return OpenFangPipeline(planner=_FixedPlanner(risk="medium"), scheduler=scheduler)


def test_park_then_approve_unblocks_second_run():
    tokens = TokenRegistry()
    bridge = PermissionBridge(tokens=tokens)
    brief = Brief(question="rewoo vs react")

    # Run 1 — no token; medium-risk node must park.
    pipeline = _build_pipeline(bridge)
    r1 = pipeline.run(brief)
    assert "gated" in r1.parked_nodes
    assert r1.failed_nodes == []

    # User grants a session-scope token.
    tokens.grant("search.github", kind="session")

    # Run 2 — same pipeline, same brief; gated node now proceeds.
    r2 = _build_pipeline(bridge).run(brief)
    assert r2.parked_nodes == []
    assert r2.failed_nodes == []
