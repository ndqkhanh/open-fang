from __future__ import annotations

import json

from harness_core.models import MockLLM

from open_fang.models import Brief, Claim, Evidence, Report, Section, SourceRef
from open_fang.verify.claim_verifier import ClaimVerifier


def _report(claims: list[Claim]) -> Report:
    return Report(
        brief=Brief(question="x"),
        sections=[Section(title="s", claims=claims)],
        references=[],
    )


def test_verifier_uses_llm_judge_when_wired(canned_evidence):
    # LLM says "not_supported" → reject even though lexical overlap passes.
    llm = MockLLM(scripted_outputs=[json.dumps({"verdict": "not_supported", "span": ""})])
    report = _report(
        [Claim(text="ReWOO decouples reasoning from observations.", evidence_ids=["e1"])]
    )
    ClaimVerifier(llm=llm).verify(report, canned_evidence)
    assert report.verified_claims == 0
    assert "llm judge" in report.sections[0].claims[0].verification_note


def test_verifier_passes_claim_when_lexical_and_llm_agree(canned_evidence):
    llm = MockLLM(scripted_outputs=[json.dumps({"verdict": "supported", "span": "decouples"})])
    report = _report(
        [Claim(text="ReWOO decouples reasoning from observations.", evidence_ids=["e1"])]
    )
    ClaimVerifier(llm=llm).verify(report, canned_evidence)
    assert report.verified_claims == 1
    assert report.faithfulness_ratio == 1.0


def test_verifier_skips_llm_when_lexical_rejects(canned_evidence):
    """Lexical failure short-circuits; the LLM is never consulted (cheaper)."""
    llm = MockLLM(scripted_outputs=[])  # would crash if consulted beyond script
    report = _report([Claim(text="totally unrelated indexed database gossip", evidence_ids=["e1"])])
    ClaimVerifier(llm=llm).verify(report, canned_evidence)
    assert report.verified_claims == 0
    # Pre-filter should catch it; the LLM judge verdict is "done" by MockLLM default
    # but the lexical rejection wins; note should reflect lexical failure.
    note = report.sections[0].claims[0].verification_note
    assert "lexical" in note or "no evidence" in note or "not found" in note


def test_verifier_marks_cross_channel_confirmed_when_multiple_channels():
    body_ev = Evidence(
        id="e-body",
        source=SourceRef(kind="arxiv", identifier="arxiv:x"),
        content="ReWOO decouples reasoning from observations.",
        channel="body",
    )
    abs_ev = Evidence(
        id="e-abs",
        source=SourceRef(kind="arxiv", identifier="arxiv:x"),
        content="ReWOO decouples reasoning from observations.",
        channel="abstract",
    )
    report = _report(
        [
            Claim(
                text="ReWOO decouples reasoning from observations.",
                evidence_ids=["e-body", "e-abs"],
            )
        ]
    )
    ClaimVerifier().verify(report, [body_ev, abs_ev])
    assert report.sections[0].claims[0].verified is True
    assert report.sections[0].claims[0].cross_channel_confirmed is True


def test_verifier_does_not_flag_cross_channel_on_single_channel(canned_evidence):
    report = _report(
        [Claim(text="ReWOO decouples reasoning from observations.", evidence_ids=["e1"])]
    )
    ClaimVerifier().verify(report, canned_evidence)
    assert report.sections[0].claims[0].cross_channel_confirmed is False
