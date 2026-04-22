"""CriticAgent: chain-of-verification / self-refine pass over verified claims.

For each claim the verifier marked `verified`, the critic:
  1. Rephrases the claim as a direct question to the evidence.
  2. Asks the LLM to answer the question using only the cited evidence.
  3. If the answer disagrees with the original claim, downgrades the claim to
     `verified=False` with a note, and returns the list of downgraded ids.

No-op unless an LLMProvider is wired; critic on a fresh Report preserves state.
"""
from __future__ import annotations

from dataclasses import dataclass

from harness_core.messages import Message
from harness_core.models import LLMProvider

from ..models import Claim, Evidence, Report

_SYSTEM = """You are the CriticAgent for chain-of-verification.
Given a CLAIM and the EVIDENCE it cites, return ONLY JSON:
{"agrees": true | false, "reason": "<short reason>"}
Say `false` if the claim overstates, misattributes, fabricates a number, or
says something the evidence does not directly support."""


@dataclass
class CritiqueResult:
    downgraded: list[str]  # claim ids


class CriticAgent:
    def __init__(self, *, llm: LLMProvider | None = None) -> None:
        self.llm = llm

    def critique(self, report: Report, evidence: list[Evidence]) -> CritiqueResult:
        if self.llm is None:
            return CritiqueResult(downgraded=[])
        by_id: dict[str, Evidence] = {e.id: e for e in evidence}
        downgraded: list[str] = []
        for section in report.sections:
            for claim in section.claims:
                if not claim.verified:
                    continue
                if not self._agrees(claim, by_id):
                    claim.verified = False
                    claim.verification_note = (
                        claim.verification_note or "critic: disagrees with evidence"
                    )
                    downgraded.append(claim.id)
        if downgraded:
            total = sum(len(s.claims) for s in report.sections)
            verified = sum(1 for s in report.sections for c in s.claims if c.verified)
            report.total_claims = total
            report.verified_claims = verified
            report.faithfulness_ratio = (verified / total) if total else 1.0
        return CritiqueResult(downgraded=downgraded)

    def _agrees(self, claim: Claim, by_id: dict[str, Evidence]) -> bool:
        import json

        assert self.llm is not None
        contents = [by_id[eid].content for eid in claim.evidence_ids if eid in by_id]
        if not contents:
            return False
        evidence_block = "\n---\n".join(f"[evidence {i + 1}] {c}" for i, c in enumerate(contents))
        reply = self.llm.generate(
            messages=[
                Message.system(_SYSTEM),
                Message.user(
                    f"CLAIM:\n{claim.text}\n\nEVIDENCE:\n{evidence_block}\n\n"
                    "Emit the JSON verdict now."
                ),
            ],
            max_tokens=200,
            temperature=0.0,
        )
        raw = (reply.content or "").strip()
        try:
            data = json.loads(raw)
            return bool(data.get("agrees", False))
        except (json.JSONDecodeError, TypeError):
            lowered = raw.lower()
            return "true" in lowered and "false" not in lowered
