from __future__ import annotations

from open_fang.models import Brief, Claim, Report, Section, SourceRef
from open_fang.verify.claim_verifier import ClaimVerifier


def test_verifier_accepts_claim_with_lexical_overlap(canned_evidence, brief: Brief):
    report = Report(
        brief=brief,
        sections=[
            Section(
                title="findings",
                claims=[
                    Claim(
                        text="ReWOO decouples reasoning from observations.",
                        evidence_ids=["e1"],
                    )
                ],
            )
        ],
        references=[SourceRef(kind="arxiv", identifier="arxiv:2305.18323")],
    )
    ClaimVerifier().verify(report, canned_evidence)
    assert report.verified_claims == 1
    assert report.total_claims == 1
    assert report.faithfulness_ratio == 1.0


def test_verifier_rejects_claim_with_missing_evidence(canned_evidence, brief: Brief):
    report = Report(
        brief=brief,
        sections=[
            Section(
                title="findings",
                claims=[Claim(text="something", evidence_ids=["nonexistent"])],
            )
        ],
        references=[],
    )
    ClaimVerifier().verify(report, canned_evidence)
    assert report.verified_claims == 0


def test_verifier_rejects_claim_without_evidence_binding(canned_evidence, brief: Brief):
    report = Report(
        brief=brief,
        sections=[
            Section(
                title="findings",
                claims=[Claim(text="unsupported assertion", evidence_ids=[])],
            )
        ],
        references=[],
    )
    ClaimVerifier().verify(report, canned_evidence)
    assert report.verified_claims == 0
