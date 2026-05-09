"""Network-marked dogfood: hits real arxiv.org. Run with `pytest -m network`.

Phase 2 exit criterion from plan.md §7:
    "Dogfood run produces a briefing on 1 real paper with ≥3 verified claims."
"""
from __future__ import annotations

import pytest

from open_fang.models import Brief
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.arxiv import ArxivSource
from open_fang.sources.router import SourceRouter


@pytest.mark.network
def test_dogfood_real_arxiv_returns_evidence():
    router = SourceRouter(arxiv=ArxivSource(email="dogfood@open-fang.test"))
    pipeline = OpenFangPipeline(scheduler=SchedulerEngine(source=router))
    brief = Brief(
        question="ReWOO planner that decouples reasoning from observations",
        target_length_words=500,
    )
    result = pipeline.run(brief)
    report = result.report

    assert report.total_claims >= 3, f"expected ≥3 claims, got {report.total_claims}"
    assert report.verified_claims >= 1
    assert any(ref.identifier.startswith("arxiv:") for ref in report.references)
