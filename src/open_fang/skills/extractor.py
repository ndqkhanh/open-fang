"""TrajectoryExtractor: mine successful PipelineResults for reusable skills.

Ported from ECC's `/skill-create` four-stage pipeline, retargeted from git
history to OpenFang's scheduler trace:

    1. Gather   — collect successful runs (faithfulness ≥ threshold)
    2. Detect   — cluster by activated-skill signature
    3. Generate — emit a learned `SKILL.md` per cluster
    4. Provenance — attach `.provenance.json` with source trace ids + confidence

v2.1 MVP uses the activated-skill signature as the cluster key. v2.2 will
add DAG-shape and tool-sequence fingerprints.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .schema import Skill, SkillFrontmatter

if TYPE_CHECKING:
    from ..pipeline import PipelineResult


@dataclass
class ExtractedSkill:
    skill: Skill
    provenance: dict


@dataclass
class TrajectoryExtractor:
    """Mine a list of PipelineResults for reusable research skills."""

    min_faithfulness: float = 0.90
    min_trajectories: int = 2  # need at least N successes in a cluster

    def extract(self, results: list[PipelineResult]) -> list[ExtractedSkill]:
        successes = [r for r in results if r.report.faithfulness_ratio >= self.min_faithfulness]
        if not successes:
            return []

        clusters: dict[tuple[str, ...], list[PipelineResult]] = {}
        for r in successes:
            signature = tuple(sorted(r.activated_skills))
            clusters.setdefault(signature, []).append(r)

        extracted: list[ExtractedSkill] = []
        for signature, cluster_results in clusters.items():
            if len(cluster_results) < self.min_trajectories:
                continue
            if not signature:
                # No skills activated — nothing to compose from yet.
                continue
            extracted.append(self._build_skill(signature, cluster_results))
        return extracted

    def write_to(self, extracted: list[ExtractedSkill], target_dir: Path) -> list[Path]:
        """Write learned skills to `target_dir/<skill-name>/SKILL.md` + .provenance.json."""
        target_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for item in extracted:
            folder = target_dir / item.skill.name
            folder.mkdir(parents=True, exist_ok=True)
            md_path = folder / "SKILL.md"
            md_path.write_text(item.skill.raw_markdown, encoding="utf-8")
            (folder / ".provenance.json").write_text(
                json.dumps(item.provenance, indent=2), encoding="utf-8"
            )
            written.append(md_path)
        return written

    def _build_skill(
        self, signature: tuple[str, ...], results: list[PipelineResult]
    ) -> ExtractedSkill:
        name = self._cluster_name(signature)
        sources = [s for s in signature]
        n = len(results)
        avg_faith = sum(r.report.faithfulness_ratio for r in results) / n
        confidence = round(min(1.0, avg_faith * (n / (n + 1))), 3)

        description = f"Composite pattern over {', '.join(sources)} (from {n} successful trajectories)."
        md = _render_learned_skill(
            name=name,
            description=description,
            confidence=confidence,
            sources=sources,
            n=n,
            avg_faith=avg_faith,
        )
        frontmatter = SkillFrontmatter(
            name=name,
            description=description,
            origin="learned",
            confidence=confidence,
        )
        skill = Skill(
            frontmatter=frontmatter,
            overview=f"Composite derived from {n} successful runs activating {sources}.",
            when_to_activate=f"When a brief would activate any of: {', '.join(sources)}",
            raw_markdown=md,
        )
        provenance = {
            "id": uuid.uuid4().hex[:12],
            "derived_from_skills": list(sources),
            "source_trace_ids": [r.report.trace_id for r in results if r.report.trace_id],
            "source_dag_ids": [r.report.dag_id for r in results if r.report.dag_id],
            "sample_size": n,
            "avg_faithfulness": round(avg_faith, 3),
            "confidence": confidence,
        }
        return ExtractedSkill(skill=skill, provenance=provenance)

    @staticmethod
    def _cluster_name(signature: tuple[str, ...]) -> str:
        """Name a learned cluster deterministically from its skill signature."""
        return "learned-" + "+".join(signature)


def _render_learned_skill(
    *,
    name: str,
    description: str,
    confidence: float,
    sources: list[str],
    n: int,
    avg_faith: float,
) -> str:
    return (
        f"---\n"
        f"name: {name}\n"
        f'description: "{description}"\n'
        f"origin: learned\n"
        f"confidence: {confidence}\n"
        f"---\n\n"
        f"## Overview\n"
        f"Composite pattern learned from {n} successful trajectories, "
        f"average faithfulness {avg_faith:.2f}.\n\n"
        f"## When to Activate\n"
        f"When a brief would activate any of: {', '.join(sources)}.\n\n"
        f"## Concepts\n"
        f"- Source skills: {', '.join(sources)}\n"
        f"- Sample size: {n}\n"
        f"- Confidence: {confidence}\n\n"
        f"## Code Examples\n"
        f"See derived_from_skills in .provenance.json for reference trajectories.\n\n"
        f"## Anti-Patterns\n"
        f"Do not activate when the brief matches only one source skill exactly — "
        f"the atomic skill is usually a better fit.\n\n"
        f"## Best Practices\n"
        f"Re-run the extractor after 20+ new successful trajectories to tighten "
        f"confidence and detect pattern drift.\n"
    )
