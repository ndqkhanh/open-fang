"""KB promotion: write verified claims + their source papers into the KB.

Promotion gate (plan.md §3.4): an entry requires a citation anchor; nothing
enters without a source.identifier. Unverified claims are skipped.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..models import Claim, Evidence, Report
from .store import KBStore


def can_promote(claim: Claim, evidence: list[Evidence]) -> bool:
    """True iff the claim is verified and ≥1 cited evidence has a source identifier."""
    if not claim.verified:
        return False
    cited = [e for e in evidence if e.id in claim.evidence_ids]
    return any(e.source.identifier for e in cited)


@dataclass
class PromotionReport:
    papers_added: int
    claims_added: int
    skipped_unverified: int
    skipped_no_anchor: int


def promote_report(report: Report, evidence: list[Evidence], kb: KBStore) -> PromotionReport:
    """Upsert source papers for every verified claim; record claims with paper_id."""
    ev_by_id: dict[str, Evidence] = {e.id: e for e in evidence}
    seen_papers: set[str] = set()
    papers_added = 0
    claims_added = 0
    unverified = 0
    no_anchor = 0

    for section in report.sections:
        for claim in section.claims:
            if not claim.verified:
                unverified += 1
                continue
            if not can_promote(claim, evidence):
                no_anchor += 1
                continue
            anchor = next(
                (ev_by_id[eid] for eid in claim.evidence_ids if eid in ev_by_id),
                None,
            )
            if anchor is None:
                no_anchor += 1
                continue
            if anchor.source.identifier not in seen_papers:
                kb.upsert_paper(anchor.source, abstract=anchor.content)
                seen_papers.add(anchor.source.identifier)
                papers_added += 1
            kb.add_claim(
                paper_id=anchor.source.identifier,
                text=claim.text,
                channel=anchor.channel,
                verified=True,
                cross_channel_confirmed=claim.cross_channel_confirmed,
            )
            claims_added += 1

    return PromotionReport(
        papers_added=papers_added,
        claims_added=claims_added,
        skipped_unverified=unverified,
        skipped_no_anchor=no_anchor,
    )
