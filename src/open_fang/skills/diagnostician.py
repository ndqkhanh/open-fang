"""Diagnostician: read failure-trace bundles, emit guideline text for the arena.

Architecturally distinct from `CriticAgent`:
    - CriticAgent verifies a single report's single claim.
    - Diagnostician reads a cohort of *weak* reports and emits *patterns*.

Optional LLM: when an LLMProvider is wired, the diagnostician asks the LLM
for a structured JSON diagnosis. Without an LLM, falls back to a simple
pattern-counter over `verification_note` values — a deterministic but less
insightful diagnosis.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from harness_core.messages import Message
from harness_core.models import LLMProvider

from ..models import Report

if TYPE_CHECKING:
    from ..pipeline import PipelineResult

_SYSTEM = """You are OpenFang's Diagnostician.
Given a list of WEAK REPORTS (each with a low faithfulness ratio + verification
notes from rejected claims), emit ONLY JSON:
{"weaknesses": [
  {"pattern": "<one-line pattern>", "proposed_fix": "<one-line fix>",
   "affected_skills": ["skill-name-1", ...]}
]}
Return an empty list if no clear pattern emerges. No other text."""


@dataclass
class Weakness:
    pattern: str
    proposed_fix: str
    affected_skills: list[str]


@dataclass
class DiagnosticReport:
    weaknesses: list[Weakness]
    sample_size: int


class Diagnostician:
    def __init__(self, *, llm: LLMProvider | None = None, min_faithfulness: float = 0.90) -> None:
        self.llm = llm
        self.min_faithfulness = min_faithfulness

    def diagnose(self, results: list[PipelineResult]) -> DiagnosticReport:
        weak = [r for r in results if r.report.faithfulness_ratio < self.min_faithfulness]
        if not weak:
            return DiagnosticReport(weaknesses=[], sample_size=0)
        if self.llm is not None:
            return self._diagnose_via_llm(weak)
        return self._diagnose_heuristic(weak)

    def _diagnose_via_llm(self, weak: list[PipelineResult]) -> DiagnosticReport:
        assert self.llm is not None
        corpus = "\n---\n".join(_report_digest(r.report) for r in weak[:10])
        reply = self.llm.generate(
            messages=[
                Message.system(_SYSTEM),
                Message.user(f"WEAK REPORTS:\n{corpus}\n\nEmit the JSON diagnosis now."),
            ],
            max_tokens=500,
            temperature=0.0,
        )
        text = (reply.content or "").strip()
        try:
            data = json.loads(text)
            raw = data.get("weaknesses", [])
        except (json.JSONDecodeError, TypeError):
            return DiagnosticReport(weaknesses=[], sample_size=len(weak))
        weaknesses = [
            Weakness(
                pattern=str(w.get("pattern", "")),
                proposed_fix=str(w.get("proposed_fix", "")),
                affected_skills=list(w.get("affected_skills", [])),
            )
            for w in raw
            if isinstance(w, dict)
        ]
        return DiagnosticReport(weaknesses=weaknesses, sample_size=len(weak))

    def _diagnose_heuristic(self, weak: list[PipelineResult]) -> DiagnosticReport:
        """No-LLM fallback: cluster verification notes across weak claims."""
        notes: list[str] = []
        activated_counter: Counter[str] = Counter()
        for r in weak:
            for section in r.report.sections:
                for claim in section.claims:
                    if not claim.verified and claim.verification_note:
                        notes.append(claim.verification_note)
            for skill in r.activated_skills:
                activated_counter[skill] += 1

        if not notes:
            return DiagnosticReport(weaknesses=[], sample_size=len(weak))

        top_note = Counter(notes).most_common(1)[0][0]
        affected = [skill for skill, _ in activated_counter.most_common(3)]
        return DiagnosticReport(
            weaknesses=[
                Weakness(
                    pattern=f"recurring rejection: {top_note[:80]}",
                    proposed_fix="tighten synthesis binding or escalate to LLM judge",
                    affected_skills=affected,
                )
            ],
            sample_size=len(weak),
        )


def _report_digest(report: Report) -> str:
    notes = [
        c.verification_note
        for s in report.sections
        for c in s.claims
        if not c.verified and c.verification_note
    ]
    return (
        f"Q: {report.brief.question}\n"
        f"faithfulness: {report.faithfulness_ratio:.2f} "
        f"({report.verified_claims}/{report.total_claims})\n"
        f"rejected_notes: {notes}"
    )
