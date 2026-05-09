"""v2.1 arena-loop integration: one round produces a report with extracted
skills and a diagnostic; learned skills round-trip through the loader.
"""
from __future__ import annotations

from pathlib import Path

from open_fang.models import Brief
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.skills.arena import EvolvingArena
from open_fang.skills.loader import SkillLoader
from open_fang.skills.registry import SkillRegistry
from open_fang.sources.mock import MockSource


def _pipeline(canned_evidence):
    registry = SkillRegistry.from_loader(SkillLoader())
    return OpenFangPipeline(
        scheduler=SchedulerEngine(source=MockSource(canned=canned_evidence)),
        skill_registry=registry,
    )


def test_arena_round_runs_end_to_end(canned_evidence):
    pipeline = _pipeline(canned_evidence)
    arena = EvolvingArena(pipeline)
    briefs = [
        Brief(question="extract citation references"),
        Brief(question="extract citation references from paper"),
        Brief(question="find the sentence supporting the claim"),
    ]
    report = arena.round(briefs)
    assert report.total_briefs == 3
    assert report.aggregate_faithfulness >= 0.90
    # Deterministic pipeline on strong fixtures — no weaknesses to diagnose.
    assert report.weak_count == 0


def test_arena_writes_learned_skills_to_dir(tmp_path: Path, canned_evidence):
    pipeline = _pipeline(canned_evidence)
    arena = EvolvingArena(pipeline)
    briefs = [
        Brief(question="extract citation references"),
        Brief(question="extract references from the paper"),
    ]
    learned_dir = tmp_path / "learned"
    report = arena.round(briefs, write_learned_to=learned_dir)

    if report.extracted:
        # At least one learned skill was produced for this cluster.
        assert learned_dir.exists()
        md_files = list(learned_dir.glob("*/SKILL.md"))
        assert md_files
        # Round-trip through the loader confirms format validity.
        loaded = SkillLoader(search_paths=[learned_dir], min_confidence=0.0).load()
        assert loaded.skills
        assert all(s.origin == "learned" for s in loaded.skills)
        assert loaded.errors == []


def test_arena_repeated_rounds_produce_stable_extraction(canned_evidence):
    """Running the same arena round twice converges — no new clusters pop up."""
    pipeline = _pipeline(canned_evidence)
    arena = EvolvingArena(pipeline)
    briefs = [
        Brief(question="extract citation references"),
        Brief(question="extract references from paper"),
    ]
    r1 = arena.round(briefs)
    r2 = arena.round(briefs)
    # Both rounds see the same cluster signature; extraction stays stable.
    assert len(r2.extracted) == len(r1.extracted)
    if r1.extracted:
        names1 = sorted(e.skill.name for e in r1.extracted)
        names2 = sorted(e.skill.name for e in r2.extracted)
        assert names1 == names2
