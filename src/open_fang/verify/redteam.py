"""RedTeamAgent: probe a finished report for minimally-modified evidence flips.

Given a `Report` + its evidence, try to produce a tampered evidence set that
would flip a verified claim to unverified (or vice versa). Findings are
returned as `RedTeamFinding` records so they can feed the next mutation-corpus
cycle.

v2.5 MVP runs the three static probes (prompt-injection, citation-poisoning,
instruction-hiding) against every piece of evidence a verified claim cites,
re-verifies, and records any claim whose verdict changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Claim, Evidence, Report, Section
from ..security.probes import (
    CitationPoisoningProbe,
    InstructionHidingProbe,
    PromptInjectionProbe,
    SecurityProbe,
)
from .claim_verifier import ClaimVerifier


@dataclass
class RedTeamFinding:
    claim_id: str
    probe_kind: str
    pre_verified: bool
    post_verified: bool
    reason: str


@dataclass
class RedTeamReport:
    findings: list[RedTeamFinding] = field(default_factory=list)

    @property
    def flipped(self) -> list[RedTeamFinding]:
        return [f for f in self.findings if f.pre_verified != f.post_verified]


class RedTeamAgent:
    def __init__(self, *, verifier: ClaimVerifier | None = None) -> None:
        self.verifier = verifier or ClaimVerifier()
        self._probes: list[SecurityProbe] = [
            PromptInjectionProbe(),
            CitationPoisoningProbe(),
            InstructionHidingProbe(),
        ]

    def probe(self, report: Report, evidence: list[Evidence]) -> RedTeamReport:
        out = RedTeamReport()
        ev_by_id = {e.id: e for e in evidence}

        for section in report.sections:
            for claim in section.claims:
                for probe in self._probes:
                    tampered_evidence = _tamper_first_cited(
                        claim, ev_by_id, evidence, probe
                    )
                    if tampered_evidence is None:
                        continue
                    replay_claim = _clone_claim(claim, tampered_evidence)
                    replay_report = Report(
                        brief=report.brief,
                        sections=[Section(title="probe", claims=[replay_claim])],
                        references=[],
                    )
                    self.verifier.verify(replay_report, tampered_evidence)
                    out.findings.append(
                        RedTeamFinding(
                            claim_id=claim.id,
                            probe_kind=_probe_kind_of(probe),
                            pre_verified=bool(claim.verified),
                            post_verified=bool(replay_claim.verified),
                            reason=replay_claim.verification_note
                            or ("verified" if replay_claim.verified else "unverified"),
                        )
                    )
        return out


def _tamper_first_cited(
    claim: Claim,
    ev_by_id: dict[str, Evidence],
    all_evidence: list[Evidence],
    probe: SecurityProbe,
) -> list[Evidence] | None:
    target = next((ev_by_id[eid] for eid in claim.evidence_ids if eid in ev_by_id), None)
    if target is None:
        return None
    result = probe.apply(target)
    tampered = [result.tampered if e.id == target.id else e for e in all_evidence]
    # The replay claim will reference the tampered evidence id, so substitute.
    return tampered


def _clone_claim(claim: Claim, tampered_evidence: list[Evidence]) -> Claim:
    # Replace the first evidence_id with the tampered id (which differs from the original).
    if not claim.evidence_ids:
        return claim.model_copy()
    new_ids = claim.evidence_ids[:]
    # tampered_evidence includes one tampered item with a new id — find it.
    tampered_ids = {e.id for e in tampered_evidence}
    # The first original id that's NOT in tampered_ids is the one we replaced.
    replaced_idx = next(
        (i for i, eid in enumerate(new_ids) if eid not in tampered_ids), 0
    )
    # Any tampered_evidence item whose id starts with "tampered-" is the plant.
    planted = next((e.id for e in tampered_evidence if e.id.startswith("tampered-")), None)
    if planted is not None:
        new_ids[replaced_idx] = planted
    return Claim(
        text=claim.text,
        evidence_ids=new_ids,
        verified=False,
        verification_note="",
    )


def _probe_kind_of(probe: SecurityProbe) -> str:
    if isinstance(probe, PromptInjectionProbe):
        return "prompt-injection"
    if isinstance(probe, CitationPoisoningProbe):
        return "citation-poisoning"
    if isinstance(probe, InstructionHidingProbe):
        return "instruction-hiding"
    return "unknown"
