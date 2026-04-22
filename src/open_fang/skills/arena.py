"""EvolvingArena: `evaluate → diagnose → extract → promote` one-round orchestration.

v2.1 MVP — SFT-free. A round:
    1. Run `pipeline.run(brief)` for each brief in the corpus.
    2. Collect results. Diagnostician produces a DiagnosticReport over the weak set.
    3. TrajectoryExtractor mines the successful set for new learned skills.
    4. Optionally write learned skills to a `learned/` directory on disk.

Return an ArenaReport summarizing the round. A future v2.2 loop wraps this
in a nightly scheduler + brief-synthesis step from the diagnostician's
guidelines.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ..models import Brief
from .diagnostician import Diagnostician, DiagnosticReport
from .extractor import ExtractedSkill, TrajectoryExtractor

if TYPE_CHECKING:
    from ..pipeline import OpenFangPipeline, PipelineResult


@dataclass
class ArenaReport:
    total_briefs: int
    weak_count: int
    aggregate_faithfulness: float
    diagnostic: DiagnosticReport
    extracted: list[ExtractedSkill] = field(default_factory=list)


class EvolvingArena:
    def __init__(
        self,
        pipeline: OpenFangPipeline,
        *,
        diagnostician: Diagnostician | None = None,
        extractor: TrajectoryExtractor | None = None,
        min_faithfulness: float = 0.90,
    ) -> None:
        self.pipeline = pipeline
        self.diagnostician = diagnostician or Diagnostician(min_faithfulness=min_faithfulness)
        self.extractor = extractor or TrajectoryExtractor(min_faithfulness=min_faithfulness)
        self.min_faithfulness = min_faithfulness

    def round(
        self,
        briefs: list[Brief],
        *,
        write_learned_to: Path | None = None,
    ) -> ArenaReport:
        results: list[PipelineResult] = [self.pipeline.run(b) for b in briefs]
        total = len(results)
        weak = sum(1 for r in results if r.report.faithfulness_ratio < self.min_faithfulness)
        total_claims = sum(r.report.total_claims for r in results)
        verified_claims = sum(r.report.verified_claims for r in results)
        agg = (verified_claims / total_claims) if total_claims else 0.0

        diagnostic = self.diagnostician.diagnose(results)
        extracted = self.extractor.extract(results)
        if write_learned_to is not None and extracted:
            self.extractor.write_to(extracted, write_learned_to)

        return ArenaReport(
            total_briefs=total,
            weak_count=weak,
            aggregate_faithfulness=round(agg, 3),
            diagnostic=diagnostic,
            extracted=extracted,
        )
