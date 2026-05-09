from __future__ import annotations

import json

from harness_core.models import MockLLM

from open_fang.models import Claim, Evidence, SourceRef
from open_fang.verify.cross_model import CrossModelVerifier


def _cl() -> Claim:
    return Claim(text="ReWOO reduces tokens fivefold", evidence_ids=["e1"])


def _ev() -> list[Evidence]:
    return [
        Evidence(
            id="e1",
            source=SourceRef(kind="arxiv", identifier="x"),
            content="ReWOO reduces tokens fivefold relative to ReAct.",
        )
    ]


def test_review_mode_pass():
    llm = MockLLM(scripted_outputs=[json.dumps({"verdict": "pass", "reason": "supported"})])
    v = CrossModelVerifier(secondary=llm).verdict(_cl(), _ev(), mode="review")
    assert v.mode == "review"
    assert v.supported is True


def test_review_mode_fail():
    llm = MockLLM(scripted_outputs=[json.dumps({"verdict": "fail", "reason": "overclaim"})])
    v = CrossModelVerifier(secondary=llm).verdict(_cl(), _ev(), mode="review")
    assert v.supported is False


def test_adversarial_claim_withstands_attack():
    llm = MockLLM(
        scripted_outputs=[
            json.dumps({"counter_example": "none found", "withstands_attack": True})
        ]
    )
    v = CrossModelVerifier(secondary=llm).verdict(_cl(), _ev(), mode="adversarial")
    assert v.mode == "adversarial"
    assert v.supported is True
    assert "none" in v.counter_example.lower()


def test_adversarial_claim_falls_to_attack():
    llm = MockLLM(
        scripted_outputs=[
            json.dumps({"counter_example": "tenfold claim contradicts benchmark", "withstands_attack": False})
        ]
    )
    v = CrossModelVerifier(secondary=llm).verdict(_cl(), _ev(), mode="adversarial")
    assert v.supported is False
    assert v.counter_example != ""


def test_consultation_mode_emits_advisory_note():
    llm = MockLLM(
        scripted_outputs=[json.dumps({"note": "consider citing the original benchmark"})]
    )
    v = CrossModelVerifier(secondary=llm).verdict(_cl(), _ev(), mode="consultation")
    assert v.mode == "consultation"
    assert v.supported is None
    assert "benchmark" in v.advisory_note


def test_malformed_json_review_falls_back_to_string_match():
    llm = MockLLM(scripted_outputs=["the claim can pass review"])
    v = CrossModelVerifier(secondary=llm).verdict(_cl(), _ev(), mode="review")
    assert v.supported is True  # contains 'pass' and not 'fail'


def test_malformed_json_adversarial_defaults_to_withstanding():
    """Conservative: if the secondary can't produce valid JSON, claim stands."""
    llm = MockLLM(scripted_outputs=["uninterpretable response"])
    v = CrossModelVerifier(secondary=llm).verdict(_cl(), _ev(), mode="adversarial")
    assert v.supported is True


def test_unknown_mode_raises():
    import pytest

    llm = MockLLM(scripted_outputs=[])
    with pytest.raises(ValueError):
        CrossModelVerifier(secondary=llm).verdict(_cl(), _ev(), mode="nonexistent")  # type: ignore[arg-type]
