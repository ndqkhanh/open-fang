"""OpenFang skills-adapter smoke test."""
from __future__ import annotations

from openfang.skills_adapter import OpenFangFailureExtractor


def test_verifier_rejections_yield_candidates() -> None:
    ext = OpenFangFailureExtractor.default()
    rejections = [
        {"task_id": "t-1", "query": "Q1", "answer": "wrong",
         "tier": "lexical", "reason": "missing-citation evidence"},
        {"task_id": "t-2", "query": "Q2", "answer": "wrong",
         "tier": "lexical", "reason": "missing-citation evidence"},
    ]
    out = ext.from_verifier_rejections(rejections, session_id="of-test-1")
    assert out
