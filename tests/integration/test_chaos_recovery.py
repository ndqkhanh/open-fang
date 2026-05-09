"""v2.5 chaos-recovery integration: pipeline runs under fault injection
and still produces a briefing, even when some nodes fail.
"""
from __future__ import annotations

import random

from open_fang.models import Brief
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.chaos import ChaosInjector, ChaosRule
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.scheduler.retries import RetryPolicy
from open_fang.sources.mock import MockSource


def _chaos(kind: str, p: float, seed: int = 0) -> ChaosInjector:
    return ChaosInjector(rules=[ChaosRule(kind=kind, probability=p)], rng=random.Random(seed))


def test_high_network_drop_pipeline_still_completes(canned_evidence):
    """Even at network_drop=1.0 the pipeline completes — retries exhaust,
    nodes fail, but downstream pipeline (synthesis/verifier) still runs on
    whatever evidence accumulated."""
    scheduler = SchedulerEngine(
        source=MockSource(canned=canned_evidence),
        retry_policy=RetryPolicy(max_attempts=1, base_delay_s=0.0),
        chaos=_chaos("network_drop", 1.0),
    )
    pipeline = OpenFangPipeline(scheduler=scheduler)
    result = pipeline.run(Brief(question="what is rewoo"))
    # All search nodes drop, so no evidence; but pipeline completes.
    assert len(result.failed_nodes) >= 1
    assert result.report is not None
    assert result.report.faithfulness_ratio >= 0.0  # defined even with 0 claims


def test_moderate_network_drop_recovers_via_retries(canned_evidence):
    """With retries enabled and moderate drop rate, the pipeline mostly
    recovers — some nodes will have required 2+ attempts but eventually
    succeed or fail gracefully."""
    scheduler = SchedulerEngine(
        source=MockSource(canned=canned_evidence),
        retry_policy=RetryPolicy(max_attempts=5, base_delay_s=0.0),
        chaos=_chaos("network_drop", 0.3, seed=7),
    )
    result = OpenFangPipeline(scheduler=scheduler).run(Brief(question="what is rewoo"))
    # Result has a report regardless; pipeline didn't crash.
    assert result.report is not None


def test_memory_drop_does_not_crash_pipeline(canned_evidence):
    """KB `kb.lookup` occasionally returns empty (simulating cache miss).
    The pipeline should complete with degraded but valid output."""
    from open_fang.kb.store import KBStore

    kb = KBStore(db_path=":memory:").open()
    scheduler = SchedulerEngine(
        source=MockSource(canned=canned_evidence),
        kb=kb,
        chaos=_chaos("memory_drop", 0.5, seed=11),
    )
    result = OpenFangPipeline(scheduler=scheduler, kb=kb).run(
        Brief(question="what is rewoo")
    )
    assert result.report is not None
    assert result.failed_nodes == []  # memory_drop degrades; it doesn't fail


def test_zero_chaos_pipeline_matches_vanilla_behavior(canned_evidence):
    """A ChaosInjector with no rules should be indistinguishable from None."""
    scheduler = SchedulerEngine(
        source=MockSource(canned=canned_evidence),
        chaos=ChaosInjector(),
    )
    result = OpenFangPipeline(scheduler=scheduler).run(Brief(question="rewoo"))
    assert result.failed_nodes == []
    assert result.report.total_claims >= 1
