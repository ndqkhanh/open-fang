"""Phase-3 exit criterion (plan.md §7): faithfulness ≥ 0.90 on the 5-paper set.

Uses the lexical-pre-filter verifier (no LLM needed) across five realistic AI/agent
papers. The 5-paper set is hand-authored in tests/fixtures/paper_data.py.
"""
from __future__ import annotations

import json

import pytest
from harness_core.models import MockLLM

from open_fang.models import Brief, Evidence
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.mock import MockSource
from open_fang.verify.claim_verifier import ClaimVerifier
from open_fang.verify.critic import CriticAgent
from tests.fixtures.paper_data import FIXTURES


def _run_pipeline(brief: Brief, evidence: list[Evidence], *, with_llm_judge: bool = False):
    scheduler = SchedulerEngine(source=MockSource(canned=evidence))
    verifier = (
        ClaimVerifier(llm=MockLLM(scripted_outputs=[json.dumps({"verdict": "supported", "span": ""})] * 50))
        if with_llm_judge
        else ClaimVerifier()
    )
    critic = CriticAgent()  # no-op without LLM
    pipeline = OpenFangPipeline(scheduler=scheduler, verifier=verifier, critic=critic)
    return pipeline.run(brief)


@pytest.mark.parametrize("idx", range(len(FIXTURES)))
def test_single_paper_faithfulness_at_or_above_gate(idx: int):
    fixture = FIXTURES[idx]
    result = _run_pipeline(fixture["brief"], fixture["evidence"])
    report = result.report
    assert report.total_claims >= 2, (
        f"fixture {idx}: synthesis produced too few claims ({report.total_claims})"
    )
    assert report.faithfulness_ratio >= 0.90, (
        f"fixture {idx}: faithfulness {report.faithfulness_ratio:.2f} < 0.90 "
        f"({report.verified_claims}/{report.total_claims} verified)"
    )


def test_aggregate_faithfulness_ratio_across_five_papers():
    total = 0
    verified = 0
    for fixture in FIXTURES:
        report = _run_pipeline(fixture["brief"], fixture["evidence"]).report
        total += report.total_claims
        verified += report.verified_claims
    assert total > 0
    ratio = verified / total
    assert ratio >= 0.90, f"aggregate faithfulness {ratio:.2f} < 0.90 ({verified}/{total})"


def test_five_paper_set_with_llm_judge_layer():
    """With an always-supported LLM judge, lexical+LLM stack stays ≥0.90."""
    total = 0
    verified = 0
    for fixture in FIXTURES:
        report = _run_pipeline(
            fixture["brief"], fixture["evidence"], with_llm_judge=True
        ).report
        total += report.total_claims
        verified += report.verified_claims
    ratio = verified / total if total else 0.0
    assert ratio >= 0.90, f"lexical+LLM ratio {ratio:.2f} < 0.90"
