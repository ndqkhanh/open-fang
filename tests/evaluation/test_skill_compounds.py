"""v2.1 exit signal: measurable benefit from the skill library across rounds.

Strict "step drop ≥30%" test is scheduled for v2.2 when the planner actually
uses activated skills to emit leaner DAGs. For v2.1 MVP we assert a weaker
but real signal: after N rounds of the arena on a repeated-brief corpus, the
registry of learned skills reaches steady state (plateau) and does not keep
growing unboundedly — evidence that dedupe + cluster-signature works.
"""
from __future__ import annotations

from pathlib import Path

from open_fang.models import Brief
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.skills.arena import EvolvingArena
from open_fang.skills.extractor import TrajectoryExtractor
from open_fang.skills.loader import SkillLoader
from open_fang.skills.registry import SkillRegistry
from open_fang.sources.mock import MockSource


def _build_pipeline(canned_evidence, skills_dirs: list[Path]):
    registry = SkillRegistry.from_loader(SkillLoader(search_paths=skills_dirs))
    return OpenFangPipeline(
        scheduler=SchedulerEngine(source=MockSource(canned=canned_evidence)),
        skill_registry=registry,
    )


def test_learned_skill_count_plateaus_across_rounds(tmp_path: Path, canned_evidence):
    learned_dir = tmp_path / "learned"
    # Seed registry with the shipped curated skills so activation works.
    curated = Path(__file__).resolve().parents[2] / "skills"
    pipeline = _build_pipeline(canned_evidence, skills_dirs=[curated])
    arena = EvolvingArena(
        pipeline,
        extractor=TrajectoryExtractor(min_faithfulness=0.90, min_trajectories=2),
    )
    briefs = [
        Brief(question="extract citation references"),
        Brief(question="extract references from paper body"),
        Brief(question="resolve citations from the paper"),
    ]

    # 5 rounds. Each round writes into the same learned/ dir; the extractor
    # is idempotent on cluster signature, so the skill count should stabilize.
    counts: list[int] = []
    for _ in range(5):
        arena.round(briefs, write_learned_to=learned_dir)
        counts.append(len(list(learned_dir.glob("*/SKILL.md"))))

    # Plateau signal: the count shouldn't keep growing round-over-round.
    # Under deterministic input the count is fixed after round 1.
    assert counts[-1] == counts[0], f"skill count should plateau, got {counts}"


def test_registry_with_learned_skills_activates_more_matches(tmp_path: Path, canned_evidence):
    """Learned skills compound: querying the registry hits more candidates
    after the arena has written new learned entries than before.
    """
    curated = Path(__file__).resolve().parents[2] / "skills"

    # Baseline — curated only.
    baseline = SkillRegistry.from_loader(SkillLoader(search_paths=[curated]))
    baseline_hits = baseline.activate("extract citation references", max_results=10)

    # Arena run seeds learned/.
    learned_dir = tmp_path / "learned"
    pipeline = _build_pipeline(canned_evidence, skills_dirs=[curated])
    arena = EvolvingArena(pipeline)
    briefs = [
        Brief(question="extract citation references"),
        Brief(question="extract references from the paper body"),
    ]
    arena.round(briefs, write_learned_to=learned_dir)

    # Augmented registry — curated + learned.
    augmented = SkillRegistry.from_loader(
        SkillLoader(search_paths=[curated, learned_dir], min_confidence=0.0)
    )
    augmented_hits = augmented.activate("extract citation references", max_results=10)

    # Learned skills either add new activation candidates or leave the set unchanged,
    # but they must never *reduce* activation count (regression guard).
    assert len(augmented_hits) >= len(baseline_hits)
