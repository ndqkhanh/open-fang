"""v7.0 integration — large source payloads stay context-lean via the sandbox.

Exit criterion (v7-plan.md §5): ≥ 30% context-token drop on large-result briefs.
"""
from __future__ import annotations

import pytest

from open_fang.kb.store import KBStore
from open_fang.memory.sandbox import ToolOutputSandbox
from open_fang.models import Brief, Evidence, SourceRef
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.mock import MockSource


def _big_payload(n: int) -> list[Evidence]:
    return [
        Evidence(
            id=f"e{i:04d}",
            source=SourceRef(
                kind="arxiv",
                identifier=f"arxiv:{i:04d}",
                title=f"Paper {i}",
            ),
            # 200 chars per item → ~100 items * 200 = 20KB well above 5KB threshold
            content=f"Research topic_{i}. " + ("lorem ipsum " * 20),
            channel="abstract",
            relevance=max(0.0, 1.0 - i * 0.005),
        )
        for i in range(n)
    ]


@pytest.fixture
def kb() -> KBStore:
    return KBStore(db_path=":memory:").open()


def test_sandbox_trims_large_evidence_payload_in_pipeline(kb: KBStore):
    evidence = _big_payload(100)
    sandbox = ToolOutputSandbox(kb, threshold_bytes=5000)
    scheduler = SchedulerEngine(
        source=MockSource(canned=evidence),
        sandbox=sandbox,
        sandbox_top_k=5,
    )
    pipeline = OpenFangPipeline(scheduler=scheduler)

    result = pipeline.run(Brief(question="topic_0"))
    total_claims = result.report.total_claims

    # Without sandbox this would produce ≥ 100 claims (one per evidence);
    # with sandbox, only the top-5 items per search node make it through.
    # Our canonical DAG has 2 search-kind nodes (survey + a broader search),
    # so the cap is 2 × 5 = 10 claims (plus some non-search noise, stays < 15).
    assert total_claims <= 15, f"too many claims landed in context: {total_claims}"

    # And: sandbox recorded the event.
    assert sandbox.stats.total_sandboxed >= 1
    assert sandbox.stats.total_items_stored >= 100  # all originals stored
    # Handle is exposed so downstream code can retrieve the other 95.
    assert scheduler.last_sandbox_handles  # non-empty


def test_small_payloads_bypass_sandbox(kb: KBStore):
    small = [
        Evidence(
            id="e1",
            source=SourceRef(kind="arxiv", identifier="arxiv:x", title="small"),
            content="tiny",
        )
    ]
    sandbox = ToolOutputSandbox(kb, threshold_bytes=5000)
    scheduler = SchedulerEngine(
        source=MockSource(canned=small),
        sandbox=sandbox,
    )
    pipeline = OpenFangPipeline(scheduler=scheduler)
    pipeline.run(Brief(question="tiny"))

    assert sandbox.stats.total_sandboxed == 0
    assert scheduler.last_sandbox_handles == {}


def test_sandbox_retrieve_finds_items_left_out_of_top_k(kb: KBStore):
    evidence = _big_payload(40)
    sandbox = ToolOutputSandbox(kb, threshold_bytes=0)  # always sandbox
    scheduler = SchedulerEngine(
        source=MockSource(canned=evidence),
        sandbox=sandbox,
        sandbox_top_k=3,
    )
    OpenFangPipeline(scheduler=scheduler).run(Brief(question="topic_0"))

    # Each search node produced a distinct sandbox handle.
    handles = list(scheduler.last_sandbox_handles.values())
    assert handles

    # topic_37 is NOT in the top-3 (relevance ordered) of any handle.
    # But BM25 retrieval finds it in at least one.
    found_anywhere = False
    for handle in handles:
        hits = sandbox.retrieve(handle, "topic_37", limit=5)
        if any(e.id == "e0037" for e in hits):
            found_anywhere = True
            break
    assert found_anywhere, "sandbox retrieve failed to surface a deferred item"
