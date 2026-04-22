"""Phase-1 retry integration: a flaky source fails N times then succeeds; scheduler recovers."""
from __future__ import annotations

from open_fang.models import Brief, Evidence
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.scheduler.retries import RetryPolicy


class FlakySource:
    """Fails the first `fail_first` calls, then returns `payload`."""

    def __init__(self, payload: list[Evidence], *, fail_first: int = 2) -> None:
        self._payload = payload
        self._fail_first = fail_first
        self.call_count = 0

    def search(self, query: str, *, max_results: int = 3) -> list[Evidence]:  # noqa: ARG002
        self.call_count += 1
        if self.call_count <= self._fail_first:
            raise RuntimeError(f"flaky failure {self.call_count}")
        return list(self._payload)


def test_scheduler_retries_and_recovers(canned_evidence):
    source = FlakySource(canned_evidence, fail_first=2)
    scheduler = SchedulerEngine(
        source=source,
        retry_policy=RetryPolicy(max_attempts=3, base_delay_s=0.0),
    )
    pipeline = OpenFangPipeline(scheduler=scheduler)

    result = pipeline.run(Brief(question="rewoo vs react"))

    assert source.call_count == 3  # 2 failures + 1 success on the arxiv node
    assert result.failed_nodes == []
    assert result.report.total_claims >= 1


def test_scheduler_gives_up_after_max_attempts(canned_evidence):
    source = FlakySource(canned_evidence, fail_first=10)
    scheduler = SchedulerEngine(
        source=source,
        retry_policy=RetryPolicy(max_attempts=3, base_delay_s=0.0),
    )
    pipeline = OpenFangPipeline(scheduler=scheduler)

    result = pipeline.run(Brief(question="rewoo vs react"))

    # Arxiv node should have failed; downstream nodes that depended on it should
    # not have run — so failed_nodes is non-empty but the run still completes.
    assert result.failed_nodes
    assert source.call_count == 3  # capped at max_attempts

    # Unused fixture import keeps the conftest evidence available for other tests.
    _ = canned_evidence
