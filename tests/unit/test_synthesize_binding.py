from __future__ import annotations

from open_fang.models import Brief
from open_fang.synthesize.writer import SynthesisWriter


def test_every_claim_binds_to_at_least_one_evidence(canned_evidence, brief: Brief):
    report = SynthesisWriter().write(brief, canned_evidence)
    assert report.sections
    for section in report.sections:
        for claim in section.claims:
            assert claim.evidence_ids, "claim must carry structural evidence ids"


def test_empty_evidence_returns_empty_findings(brief: Brief):
    report = SynthesisWriter().write(brief, [])
    assert report.sections and report.sections[0].claims == []
