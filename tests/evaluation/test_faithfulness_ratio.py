"""Phase-0 smoke: faithfulness ratio is computed and in [0, 1].

The ≥0.90 gate lands in Phase 3 once the LLM judge + cross-channel checks ship.
"""
from __future__ import annotations

from open_fang.models import Brief
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.mock import MockSource


def test_faithfulness_ratio_in_range(canned_evidence):
    pipeline = OpenFangPipeline(
        scheduler=SchedulerEngine(source=MockSource(canned=canned_evidence)),
    )
    report = pipeline.run(Brief(question="rewoo vs react")).report
    assert 0.0 <= report.faithfulness_ratio <= 1.0
