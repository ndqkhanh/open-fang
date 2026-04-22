from __future__ import annotations

from open_fang.models import Brief, Claim, Node, Report, Section
from open_fang.observe.degradation import DegradationMonitor
from open_fang.pipeline import PipelineResult
from open_fang.scheduler.loop_detector import LoopDetector, canonical_key


def _result(faithfulness: float = 1.0, n_claims: int = 3, warnings: int = 0) -> PipelineResult:
    claims = [
        Claim(text=f"c{i}", evidence_ids=["e1"], verified=True,
              mutation_warning=(i < warnings))
        for i in range(n_claims)
    ]
    return PipelineResult(
        report=Report(
            brief=Brief(question="q"),
            sections=[Section(title="s", claims=claims)],
            references=[],
            faithfulness_ratio=faithfulness,
            verified_claims=n_claims,
            total_claims=n_claims,
            dag_id="d-1",
        ),
        parked_nodes=[],
        failed_nodes=[],
        downgraded_claims=[],
    )


def test_monitor_emits_s_grade_on_perfect_run():
    m = DegradationMonitor()
    m.observe(_result(faithfulness=1.0))
    report = m.evaluate(_result(faithfulness=1.0))
    assert report.aggregate == "S"
    assert report.should_checkpoint is False


def test_monitor_drops_grade_on_poor_faithfulness():
    m = DegradationMonitor()
    for _ in range(5):
        m.observe(_result(faithfulness=0.70))
    report = m.evaluate(_result(faithfulness=0.70))
    assert report.grades["faithfulness_trend"].grade == "F"


def test_monitor_triggers_checkpoint_when_3_plus_signals_below_C():
    m = DegradationMonitor()
    bad = PipelineResult(
        report=Report(
            brief=Brief(question="q"),
            sections=[Section(title="s", claims=[
                Claim(text="c", evidence_ids=[],
                      verified=True, mutation_warning=True,
                      verification_note="note"),
            ])],
            references=[],
            faithfulness_ratio=0.5,
            verified_claims=1,
            total_claims=1,
            dag_id="d",
        ),
        parked_nodes=[],
        failed_nodes=["n1", "n2"],
        downgraded_claims=["c1"],
    )
    report = m.evaluate(bad)
    assert report.should_checkpoint is True


def test_canonical_key_is_stable_across_arg_order():
    a = Node(id="x", kind="search.arxiv", args={"query": "q", "max_results": 5})
    b = Node(id="y", kind="search.arxiv", args={"max_results": 5, "query": "q"})
    assert canonical_key(a) == canonical_key(b)


def test_canonical_key_differs_on_different_kinds():
    a = Node(id="x", kind="search.arxiv", args={"query": "q"})
    b = Node(id="y", kind="search.github", args={"query": "q"})
    assert canonical_key(a) != canonical_key(b)


def test_loop_detector_records_and_retrieves():
    d = LoopDetector()
    n = Node(id="x", kind="search.arxiv", args={"query": "q"})
    assert d.saw_before(n) is False
    d.record(n, "canned-output")
    assert d.saw_before(n) is True
    assert d.cached_output(n) == "canned-output"
    assert d.hit_count == 1


def test_loop_detector_reset():
    d = LoopDetector()
    n = Node(id="x", kind="search.arxiv", args={"q": "x"})
    d.record(n, 1)
    d.reset()
    assert d.saw_before(n) is False
    assert d.hit_count == 0
