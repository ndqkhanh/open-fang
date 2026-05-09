from __future__ import annotations

from open_fang.attribution.primitives import Primitive
from open_fang.chaos_scanner import (
    ChaosScanner,
    FragilityMatrix,
    make_default_pipeline_factory,
)
from open_fang.models import Brief
from open_fang.scheduler.retries import RetryPolicy
from open_fang.sources.mock import MockSource


def _factory_no_retries(canned_evidence):
    def factory(injector):
        from open_fang.pipeline import OpenFangPipeline
        from open_fang.scheduler.engine import SchedulerEngine

        scheduler = SchedulerEngine(
            source=MockSource(canned=canned_evidence),
            chaos=injector,
            retry_policy=RetryPolicy(max_attempts=1, base_delay_s=0.0),
        )
        return OpenFangPipeline(scheduler=scheduler)

    return factory


def test_scanner_aggregates_attributions_across_rounds(canned_evidence):
    scanner = ChaosScanner(pipeline_factory=_factory_no_retries(canned_evidence))
    matrix = scanner.scan(
        Brief(question="rewoo vs react"),
        configs=[("network_drop", 1.0)],
        rounds=3,
    )
    assert isinstance(matrix, FragilityMatrix)
    assert len(matrix.entries) == 1
    entry = matrix.entries[0]
    assert entry.total_runs == 3
    # network_drop=1.0 + max_attempts=1 guarantees every run fails at search.arxiv
    # → at least one attribution per run → total_attributions ≥ 3.
    assert entry.total_attributions >= 3
    # The top primitive should be SOURCE_ROUTER (what our classifier attributes
    # failed-node crashes to).
    top = entry.top_primitive()
    assert top is not None
    assert top[0] == Primitive.SOURCE_ROUTER


def test_scanner_handles_multiple_configs(canned_evidence):
    scanner = ChaosScanner(pipeline_factory=_factory_no_retries(canned_evidence))
    matrix = scanner.scan(
        Brief(question="rewoo"),
        configs=[("network_drop", 1.0), ("memory_drop", 0.0)],
        rounds=2,
    )
    assert len(matrix.entries) == 2
    # With network_drop=1.0: all runs should fail, producing attributions.
    assert matrix.entries[0].total_attributions >= 2
    # With memory_drop=0.0: no chaos fires, no failure attributions expected.
    assert matrix.entries[1].total_attributions == 0


def test_scanner_zero_chaos_produces_no_attributions(canned_evidence):
    scanner = ChaosScanner(pipeline_factory=_factory_no_retries(canned_evidence))
    matrix = scanner.scan(
        Brief(question="rewoo"),
        configs=[("network_drop", 0.0)],
        rounds=3,
    )
    entry = matrix.entries[0]
    assert entry.total_runs == 3
    # Clean runs → no attributions triggered.
    assert entry.total_attributions == 0


def test_to_rows_returns_serializable_payload(canned_evidence):
    scanner = ChaosScanner(pipeline_factory=_factory_no_retries(canned_evidence))
    matrix = scanner.scan(
        Brief(question="x"),
        configs=[("network_drop", 1.0)],
        rounds=2,
    )
    rows = matrix.to_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row["chaos_mode"] == "network_drop"
    assert row["probability"] == 1.0
    assert "primitive_counts" in row
    # Keys should be strings (Primitive.value), not enum members.
    for k in row["primitive_counts"]:
        assert isinstance(k, str)


def test_default_pipeline_factory_constructs_pipeline():
    factory = make_default_pipeline_factory(source=MockSource())
    from open_fang.scheduler.chaos import ChaosInjector

    pipeline = factory(ChaosInjector())
    assert pipeline is not None
    # Can run a brief end-to-end.
    result = pipeline.run(Brief(question="rewoo"))
    assert result.report is not None
