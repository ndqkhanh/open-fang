from __future__ import annotations

import json

from harness_core.models import MockLLM

from open_fang.models import Brief, Claim, Evidence, Report, Section, SourceRef
from open_fang.verify.critic import CriticAgent


def _report_with_claim(evidence: Evidence) -> Report:
    return Report(
        brief=Brief(question="x"),
        sections=[
            Section(
                title="s",
                claims=[
                    Claim(
                        text="ReWOO decouples reasoning from observations.",
                        evidence_ids=[evidence.id],
                        verified=True,  # pre-verified by the earlier tier
                    )
                ],
            )
        ],
        references=[evidence.source],
    )


def _evidence() -> Evidence:
    return Evidence(
        id="e1",
        source=SourceRef(kind="arxiv", identifier="arxiv:x", title="x"),
        content="ReWOO decouples reasoning from observations.",
    )


def test_critic_is_noop_without_llm():
    e = _evidence()
    r = _report_with_claim(e)
    result = CriticAgent().critique(r, [e])
    assert result.downgraded == []
    assert r.sections[0].claims[0].verified is True


def test_critic_downgrades_on_disagreement():
    e = _evidence()
    r = _report_with_claim(e)
    r.total_claims = 1
    r.verified_claims = 1
    r.faithfulness_ratio = 1.0

    llm = MockLLM(scripted_outputs=[json.dumps({"agrees": False, "reason": "overstates"})])
    result = CriticAgent(llm=llm).critique(r, [e])

    assert result.downgraded == [r.sections[0].claims[0].id]
    assert r.sections[0].claims[0].verified is False
    assert r.verified_claims == 0
    assert r.faithfulness_ratio == 0.0


def test_critic_keeps_claim_on_agreement():
    e = _evidence()
    r = _report_with_claim(e)
    llm = MockLLM(scripted_outputs=[json.dumps({"agrees": True, "reason": ""})])
    result = CriticAgent(llm=llm).critique(r, [e])
    assert result.downgraded == []
    assert r.sections[0].claims[0].verified is True
