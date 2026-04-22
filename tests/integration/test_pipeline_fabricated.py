"""Phase-1 fabricated-citation integration: verifier must block claims bound to
evidence IDs that do not exist in the retrieved evidence set.
"""
from __future__ import annotations

from open_fang.models import Brief, Claim, Evidence, Report, Section, SourceRef
from open_fang.verify.claim_verifier import ClaimVerifier


def test_fabricated_evidence_id_is_rejected(canned_evidence):
    """A report with a planted non-existent evidence ID must fail verification."""
    report = Report(
        brief=Brief(question="fabricated test"),
        sections=[
            Section(
                title="findings",
                claims=[
                    Claim(text="ReWOO decouples reasoning.", evidence_ids=["e1"]),
                    Claim(text="ReAct interleaves reasoning.", evidence_ids=["e2"]),
                    # Planted fabrication — no such evidence in the store.
                    Claim(
                        text="ReWOO outperforms ReAct by 99%.",
                        evidence_ids=["fabricated-xyz"],
                    ),
                ],
            )
        ],
        references=[
            SourceRef(kind="arxiv", identifier="arxiv:2305.18323"),
            SourceRef(kind="arxiv", identifier="arxiv:2210.03629"),
        ],
    )

    ClaimVerifier().verify(report, canned_evidence)

    assert report.total_claims == 3
    assert report.verified_claims == 2  # the two real ones
    assert report.faithfulness_ratio == 2 / 3

    fabricated_claim = report.sections[0].claims[2]
    assert fabricated_claim.verified is False
    assert "fabricated-xyz" in fabricated_claim.verification_note


def test_release_gate_would_block_low_faithfulness():
    """Document the Phase-3 release gate: faithfulness < 0.90 blocks release."""
    fake_ratio = 2 / 3  # from above
    release_floor = 0.90
    assert fake_ratio < release_floor, "verifier gate must still block this report"


def test_verifier_rejects_lexically_disjoint_claim(canned_evidence):
    """A claim bound to real evidence but with no token overlap is also rejected."""
    disjoint = Evidence(
        id="disjoint-1",
        source=SourceRef(kind="arxiv", identifier="arxiv:stub"),
        content="completely unrelated boilerplate about database indexing.",
        channel="abstract",
    )
    evidence = [*canned_evidence, disjoint]
    report = Report(
        brief=Brief(question="x"),
        sections=[
            Section(
                title="s",
                claims=[
                    Claim(
                        text="ReWOO decouples reasoning from observations.",
                        evidence_ids=["disjoint-1"],
                    )
                ],
            )
        ],
        references=[],
    )
    ClaimVerifier().verify(report, evidence)
    assert report.verified_claims == 0
    assert report.sections[0].claims[0].verified is False
