from __future__ import annotations

from open_fang.models import Brief
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.mock import MockSource


def test_pipeline_happy_path(canned_evidence, brief: Brief):
    pipeline = OpenFangPipeline(
        scheduler=SchedulerEngine(source=MockSource(canned=canned_evidence)),
    )
    result = pipeline.run(brief)
    report = result.report

    assert result.failed_nodes == []
    assert report.total_claims >= 1
    assert report.faithfulness_ratio >= 0.5  # skeleton MVP; Phase 3 raises to 0.90
    # Every claim in the report must carry structural evidence ids
    for section in report.sections:
        for claim in section.claims:
            assert claim.evidence_ids


def test_pipeline_to_markdown(canned_evidence, brief: Brief):
    pipeline = OpenFangPipeline(
        scheduler=SchedulerEngine(source=MockSource(canned=canned_evidence)),
    )
    md = pipeline.run(brief).report.to_markdown()
    assert md.startswith("# ")
    assert "## References" in md
    assert "faithfulness:" in md
