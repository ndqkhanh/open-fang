"""Integration of Tiers 2 (mutation warning) and 4 (executable) into ClaimVerifier."""
from __future__ import annotations

import json

from harness_core.models import MockLLM

from open_fang.models import Brief, Claim, Evidence, Report, Section, SourceRef
from open_fang.verify.claim_verifier import ClaimVerifier, ExecutableProbe
from open_fang.verify.executable import ExecutableVerifier
from open_fang.verify.mutation import MutationProbe


def _report_with(claim: Claim) -> Report:
    return Report(
        brief=Brief(question="x"),
        sections=[Section(title="s", claims=[claim])],
        references=[],
    )


def _quant_evidence(data: dict | None = None) -> Evidence:
    return Evidence(
        id="e1",
        source=SourceRef(kind="arxiv", identifier="x"),
        content="ReWOO reduces tokens fivefold relative to ReAct.",
        structured_data=data or {"rewoo_tokens": 120, "react_tokens": 600},
    )


def test_mutation_warning_set_when_judge_not_distinguishable():
    # Judge says SUPPORTED for original + SUPPORTED for first mutant → warning.
    script = [json.dumps({"verdict": "supported", "span": ""})] * 10
    llm = MockLLM(scripted_outputs=script)
    mutation = MutationProbe(llm)
    # Second LLM drives Tier 3 (LLM judge) — keep it separate so counts are clean.
    judge_llm = MockLLM(scripted_outputs=[json.dumps({"verdict": "supported", "span": ""})])
    verifier = ClaimVerifier(llm=judge_llm, mutation_probe=mutation)

    claim = Claim(text="ReWOO reduces tokens fivefold.", evidence_ids=["e1"])
    report = _report_with(claim)
    verifier.verify(report, [_quant_evidence()])
    assert claim.verified is True  # Tier 2 warns; Tier 3 still passes
    assert claim.mutation_warning is True


def test_mutation_warning_not_set_when_judge_distinguishes():
    # Mutation probe: original SUPPORTED, mutants all NOT_SUPPORTED.
    mutation_script = [json.dumps({"verdict": "supported", "span": ""})]
    mutation_script += [json.dumps({"verdict": "not_supported", "span": ""}) for _ in range(10)]
    mutation_llm = MockLLM(scripted_outputs=mutation_script)
    mutation = MutationProbe(mutation_llm)
    judge_llm = MockLLM(scripted_outputs=[json.dumps({"verdict": "supported", "span": ""})])
    verifier = ClaimVerifier(llm=judge_llm, mutation_probe=mutation)

    claim = Claim(text="ReWOO reduces tokens fivefold.", evidence_ids=["e1"])
    report = _report_with(claim)
    verifier.verify(report, [_quant_evidence()])
    assert claim.verified is True
    assert claim.mutation_warning is False


def test_executable_tier_rejects_when_assertion_fails():
    claim = Claim(text="ReWOO reduces tokens fivefold.", evidence_ids=["e1"])
    ev = _quant_evidence({"rewoo_tokens": 400, "react_tokens": 600})  # only 1.5x
    probe = ExecutableProbe(
        scripts={
            claim.id: (
                "ratio = evidence['react_tokens'] / evidence['rewoo_tokens']\n"
                "assert ratio >= 4.0, 'claimed fivefold but ratio only %s' % ratio"
            )
        }
    )
    verifier = ClaimVerifier(
        executable_verifier=ExecutableVerifier(),
        executable_probe=probe,
    )
    report = _report_with(claim)
    verifier.verify(report, [ev])
    assert claim.verified is False
    assert claim.executable_passed is False
    assert "executable verifier rejected" in claim.verification_note


def test_executable_tier_passes_when_assertion_holds():
    claim = Claim(text="ReWOO reduces tokens fivefold.", evidence_ids=["e1"])
    ev = _quant_evidence({"rewoo_tokens": 120, "react_tokens": 600})  # 5x
    probe = ExecutableProbe(
        scripts={
            claim.id: (
                "ratio = evidence['react_tokens'] / evidence['rewoo_tokens']\n"
                "assert 4.0 <= ratio <= 6.0"
            )
        }
    )
    verifier = ClaimVerifier(
        executable_verifier=ExecutableVerifier(),
        executable_probe=probe,
    )
    report = _report_with(claim)
    verifier.verify(report, [ev])
    assert claim.verified is True
    assert claim.executable_passed is True


def test_executable_tier_skipped_without_script():
    # Claim text overlaps the evidence content so lexical Tier 1 passes.
    claim = Claim(text="ReWOO reduces tokens relative to ReAct.", evidence_ids=["e1"])
    ev = _quant_evidence()
    probe = ExecutableProbe(scripts={})  # no script for this claim
    verifier = ClaimVerifier(
        executable_verifier=ExecutableVerifier(),
        executable_probe=probe,
    )
    report = _report_with(claim)
    verifier.verify(report, [ev])
    # Lexical passes; executable_passed stays None.
    assert claim.executable_passed is None
    assert claim.verified is True
