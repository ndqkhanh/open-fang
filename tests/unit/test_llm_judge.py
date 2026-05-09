from __future__ import annotations

import json

from harness_core.models import MockLLM

from open_fang.verify.llm_judge import LLMJudge


def test_judge_parses_supported_verdict():
    llm = MockLLM(scripted_outputs=[json.dumps({"verdict": "supported", "span": "key phrase"})])
    v = LLMJudge(llm).judge("a claim", ["the evidence body"])
    assert v.supported is True
    assert v.span == "key phrase"


def test_judge_parses_not_supported_verdict():
    llm = MockLLM(scripted_outputs=[json.dumps({"verdict": "not_supported", "span": ""})])
    v = LLMJudge(llm).judge("a claim", ["the evidence body"])
    assert v.supported is False


def test_judge_falls_back_when_json_unparseable():
    llm = MockLLM(scripted_outputs=["the claim is supported by the evidence"])
    v = LLMJudge(llm).judge("a claim", ["body"])
    assert v.supported is True  # lowered-string fallback


def test_judge_fallback_rejects_not_supported_phrase():
    llm = MockLLM(scripted_outputs=["this is not_supported"])
    v = LLMJudge(llm).judge("a claim", ["body"])
    assert v.supported is False
