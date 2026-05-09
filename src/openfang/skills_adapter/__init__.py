"""OpenFang skills adapter — evolution over existing 5 skills."""
from __future__ import annotations

from dataclasses import dataclass

from harness_skills import SkillRecord
from harness_skills.extract import ExtractionContext, FailureExtractor
from harness_skills.extract.failure import FailureTrace


@dataclass
class OpenFangFailureExtractor:
    extractor: FailureExtractor

    @classmethod
    def default(cls) -> OpenFangFailureExtractor:
        return cls(extractor=FailureExtractor(family="extractor-openfang"))

    def from_verifier_rejections(self, rejections: list[dict], session_id: str) -> list[SkillRecord]:
        traces = [
            FailureTrace(
                task_id=str(r.get("task_id", "")),
                task_description=str(r.get("query", "")),
                failed_output=str(r.get("answer", "")),
                diagnostic=str(r.get("tier", "")) + " " + str(r.get("reason", "")),
            )
            for r in rejections
        ]
        return self.extractor.extract(traces, context=ExtractionContext(session_id=session_id))


__all__ = ["OpenFangFailureExtractor"]
