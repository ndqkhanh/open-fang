"""Phase-6 evaluation: run the 20-brief corpus and assert SLA floors.

Floors (plan.md §6 / §9 / system-design.md):
    - Per-brief faithfulness ≥ 0.90
    - Aggregate faithfulness ≥ 0.90
    - Per-brief Pass@5 ≥ 0.70
    - Aggregate Pass^5 ≥ 0.70

With the deterministic lexical+MockSource stack, all runs of the same brief
produce identical output so Pass@k = Pass^k = 1.0 trivially. This test fixes
the CI floor *now*; Phase 6+ flips real LLM-judge verification on and the
same floors begin to have bite.
"""
from __future__ import annotations

import pytest

from open_fang.eval.passk import summarise
from open_fang.models import Brief, Evidence
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.mock import MockSource
from tests.fixtures.briefs import BRIEFS, EvalBrief

K = 5
PER_BRIEF_FAITHFULNESS_FLOOR = 0.90
AGGREGATE_FAITHFULNESS_FLOOR = 0.90
PER_BRIEF_PASS_AT_K_FLOOR = 0.70
AGGREGATE_PASS_POW_K_FLOOR = 0.70


def _run(brief: Brief, evidence: list[Evidence]) -> float:
    pipeline = OpenFangPipeline(scheduler=SchedulerEngine(source=MockSource(canned=evidence)))
    return pipeline.run(brief).report.faithfulness_ratio


@pytest.mark.parametrize("eb", BRIEFS, ids=[b.tag for b in BRIEFS])
def test_single_brief_faithfulness(eb: EvalBrief):
    ratio = _run(eb.brief, eb.evidence)
    assert ratio >= eb.min_faithfulness, (
        f"brief {eb.tag}: faithfulness {ratio:.2f} < {eb.min_faithfulness:.2f}"
    )


def test_aggregate_faithfulness_floor():
    total = 0
    verified = 0
    for eb in BRIEFS:
        pipeline = OpenFangPipeline(scheduler=SchedulerEngine(source=MockSource(canned=eb.evidence)))
        report = pipeline.run(eb.brief).report
        total += report.total_claims
        verified += report.verified_claims
    assert total > 0
    ratio = verified / total
    assert ratio >= AGGREGATE_FAITHFULNESS_FLOOR, (
        f"aggregate faithfulness {ratio:.3f} < {AGGREGATE_FAITHFULNESS_FLOOR}"
    )


def test_per_brief_pass_at_k():
    """Pass@5 per brief: at least one of 5 deterministic runs meets its floor."""
    for eb in BRIEFS:
        results = [
            _run(eb.brief, eb.evidence) >= PER_BRIEF_FAITHFULNESS_FLOOR for _ in range(K)
        ]
        s = summarise(results, k=K)
        assert s.pass_at_k >= PER_BRIEF_PASS_AT_K_FLOOR, (
            f"{eb.tag}: Pass@{K}={s.pass_at_k:.2f} < {PER_BRIEF_PASS_AT_K_FLOOR} "
            f"(runs: {s.n_success}/{s.n_runs})"
        )


def test_aggregate_pass_pow_k_reliability():
    """Pass^5 across all 20 briefs: reliability under repeated sampling."""
    results: list[bool] = []
    for eb in BRIEFS:
        for _ in range(K):
            results.append(_run(eb.brief, eb.evidence) >= PER_BRIEF_FAITHFULNESS_FLOOR)
    s = summarise(results, k=K)
    assert s.pass_pow_k >= AGGREGATE_PASS_POW_K_FLOOR, (
        f"Pass^{K}={s.pass_pow_k:.2f} < {AGGREGATE_PASS_POW_K_FLOOR} "
        f"(runs: {s.n_success}/{s.n_runs})"
    )
