"""Synthesis writer: Evidence[] + Brief → Report with structural claim binding."""
from __future__ import annotations

from ..extract.claims import ClaimExtractor
from ..models import Brief, Claim, Evidence, Report, Section, SourceRef


class SynthesisWriter:
    """Deterministic MVP writer: one section per source kind, one claim per evidence."""

    def __init__(self, *, extractor: ClaimExtractor | None = None) -> None:
        self.extractor = extractor or ClaimExtractor()

    def write(self, brief: Brief, evidence: list[Evidence]) -> Report:
        if not evidence:
            return Report(
                brief=brief,
                summary="No evidence retrieved.",
                sections=[Section(title="Findings", claims=[])],
                references=[],
            )

        claims_by_section: dict[str, list[Claim]] = {}
        refs_by_id: dict[str, SourceRef] = {}

        for claim in self.extractor.extract(evidence):
            # Place claim in section keyed by its first evidence's source kind.
            first = next((e for e in evidence if e.id in claim.evidence_ids), None)
            if first is None:
                continue
            section_title = f"{first.source.kind.capitalize()} findings"
            claims_by_section.setdefault(section_title, []).append(claim)
            refs_by_id[first.source.identifier] = first.source

        sections = [
            Section(title=title, claims=claims)
            for title, claims in sorted(claims_by_section.items())
        ]
        return Report(
            brief=brief,
            summary=f"Briefing on: {brief.question}",
            sections=sections,
            references=list(refs_by_id.values()),
        )
