"""v2.0 exit criterion: pipeline consumes the skill registry and records
which skills were activated for a given brief.
"""
from __future__ import annotations

from open_fang.models import Brief
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.skills.loader import SkillLoader
from open_fang.skills.registry import SkillRegistry
from open_fang.sources.mock import MockSource


def test_pipeline_records_activated_skills(canned_evidence):
    registry = SkillRegistry.from_loader(SkillLoader())
    assert len(registry.list()) == 5, "curated skill library must be loaded"

    pipeline = OpenFangPipeline(
        scheduler=SchedulerEngine(source=MockSource(canned=canned_evidence)),
        skill_registry=registry,
    )
    result = pipeline.run(
        Brief(question="extract citation references from the paper's body")
    )
    # "citation-extraction" should activate on this query.
    assert "citation-extraction" in result.activated_skills
    # Pipeline still completes end-to-end with skills wired.
    assert result.failed_nodes == []
    assert result.report.total_claims >= 1


def test_pipeline_without_registry_activates_nothing(canned_evidence):
    pipeline = OpenFangPipeline(
        scheduler=SchedulerEngine(source=MockSource(canned=canned_evidence)),
    )
    result = pipeline.run(Brief(question="anything"))
    assert result.activated_skills == []
