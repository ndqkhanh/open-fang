from __future__ import annotations

from pathlib import Path

from open_fang.models import Brief, Report
from open_fang.pipeline import PipelineResult
from open_fang.skills.extractor import TrajectoryExtractor


def _result(question: str, faithfulness: float, activated: list[str]) -> PipelineResult:
    return PipelineResult(
        report=Report(
            brief=Brief(question=question),
            sections=[],
            references=[],
            faithfulness_ratio=faithfulness,
            verified_claims=int(faithfulness * 10),
            total_claims=10,
            trace_id="t-" + question[:4],
            dag_id="d-" + question[:4],
        ),
        parked_nodes=[],
        failed_nodes=[],
        downgraded_claims=[],
        activated_skills=activated,
    )


def test_extractor_requires_minimum_cluster_size():
    extractor = TrajectoryExtractor(min_faithfulness=0.90, min_trajectories=2)
    # Only 1 successful trajectory in the cluster — below min_trajectories.
    results = [_result("q1", 1.0, ["citation-extraction"])]
    assert extractor.extract(results) == []


def test_extractor_emits_learned_skill_for_cluster():
    extractor = TrajectoryExtractor(min_faithfulness=0.90, min_trajectories=2)
    results = [
        _result("q1", 1.0, ["citation-extraction"]),
        _result("q2", 0.95, ["citation-extraction"]),
        _result("q3", 1.0, ["claim-localization"]),  # different cluster — ignored
    ]
    out = extractor.extract(results)
    assert len(out) == 1
    skill = out[0].skill
    assert skill.origin == "learned"
    assert skill.frontmatter.confidence is not None
    assert 0.0 < skill.frontmatter.confidence <= 1.0
    assert "citation-extraction" in skill.name
    assert out[0].provenance["sample_size"] == 2


def test_extractor_skips_weak_trajectories():
    extractor = TrajectoryExtractor(min_faithfulness=0.90, min_trajectories=2)
    results = [
        _result("q1", 0.80, ["x"]),
        _result("q2", 0.85, ["x"]),
    ]
    assert extractor.extract(results) == []


def test_extractor_write_to_emits_md_and_provenance(tmp_path: Path):
    extractor = TrajectoryExtractor(min_faithfulness=0.90, min_trajectories=2)
    results = [
        _result("q1", 1.0, ["citation-extraction"]),
        _result("q2", 1.0, ["citation-extraction"]),
    ]
    out = extractor.extract(results)
    assert out
    written = extractor.write_to(out, tmp_path)
    assert len(written) == 1
    md = written[0]
    assert md.name == "SKILL.md"
    assert "origin: learned" in md.read_text()
    prov = md.parent / ".provenance.json"
    assert prov.exists()
    import json

    data = json.loads(prov.read_text())
    assert data["sample_size"] == 2
    assert data["derived_from_skills"] == ["citation-extraction"]


def test_extracted_skill_loads_back_through_loader(tmp_path: Path):
    """Round-trip: written learned skill is loadable by SkillLoader with min_confidence."""
    from open_fang.skills.loader import SkillLoader

    extractor = TrajectoryExtractor(min_faithfulness=0.90, min_trajectories=2)
    results = [
        _result("q1", 1.0, ["citation-extraction"]),
        _result("q2", 1.0, ["citation-extraction"]),
    ]
    extractor.write_to(extractor.extract(results), tmp_path)

    result = SkillLoader(search_paths=[tmp_path], min_confidence=0.0).load()
    names = [s.name for s in result.skills]
    assert any("citation-extraction" in n for n in names)
    assert all(s.origin == "learned" for s in result.skills)
    assert result.errors == []
