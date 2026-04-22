"""ClaimVerifier: multi-tier gate over report claims.

Tiers (run in order; later tiers only if earlier ones don't already reject):
  1. Lexical — every bound evidence id exists; claim text shares vocabulary
     with at least one cited evidence. Cheap and free.
  2. Mutation-robust (v2.4, optional) — generates numeric/signal mutants of
     the claim and asks the LLM judge to distinguish. Emits a warning flag,
     not a veto.
  3. LLM judge (optional) — structured JSON verdict on whether the cited
     evidence supports the claim.
  4. Executable (v2.4, optional) — runs a reproduction-script assertion
     against the merged structured evidence; failure vetoes the claim.
  5. Cross-channel flag (metadata only) — sets
     `claim.cross_channel_confirmed = True` when ≥2 distinct channels back
     the claim.

Faithfulness ratio = verified / total. Release floor ≥ 0.90 (plan.md §7).
"""
from __future__ import annotations

from dataclasses import dataclass

from harness_core.models import LLMProvider

from ..models import Claim, Evidence, Report
from .executable import ExecutableVerifier
from .llm_judge import LLMJudge
from .mutation import MutationProbe

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
    "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "with", "by", "as", "at",
    "we", "our", "it", "its",
}


def _tokens(text: str) -> set[str]:
    return {
        t.strip(".,;:!?\"'()[]").lower()
        for t in text.split()
        if len(t) > 3 and t.strip(".,;:!?\"'()[]").lower() not in _STOPWORDS
    }


@dataclass
class ExecutableProbe:
    """Caller-supplied assertion scripts keyed by claim id."""

    scripts: dict[str, str]

    def script_for(self, claim_id: str) -> str | None:
        return self.scripts.get(claim_id)


class ClaimVerifier:
    def __init__(
        self,
        *,
        llm: LLMProvider | None = None,
        mutation_probe: MutationProbe | None = None,
        executable_verifier: ExecutableVerifier | None = None,
        executable_probe: ExecutableProbe | None = None,
    ) -> None:
        self.judge = LLMJudge(llm) if llm is not None else None
        self.mutation_probe = mutation_probe
        self.executable_verifier = executable_verifier
        self.executable_probe = executable_probe

    def verify(self, report: Report, evidence: list[Evidence]) -> None:
        by_id: dict[str, Evidence] = {e.id: e for e in evidence}
        total = 0
        verified = 0
        for section in report.sections:
            for claim in section.claims:
                total += 1
                rejection = self._lexical_check(claim, by_id)
                if rejection is not None:
                    claim.verified = False
                    claim.verification_note = rejection
                    continue

                # Tier 2 — mutation probe. Warning only; does not veto.
                if self.mutation_probe is not None:
                    probe_result = self.mutation_probe.probe(claim, evidence)
                    if probe_result.mutants and not probe_result.distinguishable:
                        claim.mutation_warning = True

                # Tier 3 — LLM judge.
                if self.judge is not None:
                    judge_ok, note = self._llm_check(claim, by_id)
                    if not judge_ok:
                        claim.verified = False
                        claim.verification_note = note
                        continue

                # Tier 4 — executable verifier (runs only when a script is provided).
                if self.executable_verifier is not None and self.executable_probe is not None:
                    script = self.executable_probe.script_for(claim.id)
                    if script is not None:
                        result = self.executable_verifier.verify(claim, evidence, script)
                        claim.executable_passed = result.passed
                        if not result.passed:
                            claim.verified = False
                            claim.verification_note = (
                                f"executable verifier rejected: {result.error or 'assertion failed'}"
                            )
                            continue

                claim.verified = True
                claim.cross_channel_confirmed = self._has_cross_channel(claim, by_id)
                verified += 1

        report.total_claims = total
        report.verified_claims = verified
        report.faithfulness_ratio = (verified / total) if total else 1.0

    @staticmethod
    def _lexical_check(claim: Claim, by_id: dict[str, Evidence]) -> str | None:
        if not claim.evidence_ids:
            return "no evidence bound"
        for eid in claim.evidence_ids:
            if eid not in by_id:
                return f"evidence id {eid!r} not found"
        claim_tokens = _tokens(claim.text)
        for eid in claim.evidence_ids:
            if claim_tokens & _tokens(by_id[eid].content):
                return None
        return "claim has no lexical overlap with cited evidence"

    def _llm_check(
        self,
        claim: Claim,
        by_id: dict[str, Evidence],
    ) -> tuple[bool, str]:
        assert self.judge is not None
        contents = [by_id[eid].content for eid in claim.evidence_ids if eid in by_id]
        verdict = self.judge.judge(claim.text, contents)
        if verdict.supported:
            return True, ""
        note = "llm judge: not supported"
        if verdict.span:
            note = f"{note} (nearest span: {verdict.span[:120]})"
        return False, note

    @staticmethod
    def _has_cross_channel(claim: Claim, by_id: dict[str, Evidence]) -> bool:
        channels = {by_id[eid].channel for eid in claim.evidence_ids if eid in by_id}
        return len(channels) >= 2
