from __future__ import annotations

from open_fang.attribution import HAFCClassifier, Primitive
from open_fang.models import Brief, Claim, Report, Section
from open_fang.pipeline import PipelineResult


def _result(
    *,
    claims: list[Claim] | None = None,
    failed_nodes: list[str] | None = None,
    parked_nodes: list[str] | None = None,
    downgraded_claims: list[str] | None = None,
    faithfulness: float = 1.0,
    dag_id: str = "d-abc",
) -> PipelineResult:
    return PipelineResult(
        report=Report(
            brief=Brief(question="rewoo"),
            sections=[Section(title="s", claims=claims or [])],
            references=[],
            faithfulness_ratio=faithfulness,
            verified_claims=sum(1 for c in (claims or []) if c.verified),
            total_claims=len(claims or []),
            dag_id=dag_id,
        ),
        parked_nodes=parked_nodes or [],
        failed_nodes=failed_nodes or [],
        downgraded_claims=downgraded_claims or [],
    )


def test_all_12_primitives_exist():
    # Versioned vocabulary: adding/removing primitives is a breaking change.
    from open_fang.attribution import PRIMITIVES

    assert len(PRIMITIVES) == 12


def test_clean_run_no_attribution():
    classifier = HAFCClassifier()
    report = classifier.classify(_result())
    assert report.results == []
    assert report.total_failures == 0


def test_failed_node_attributes_to_source_router():
    classifier = HAFCClassifier()
    report = classifier.classify(_result(failed_nodes=["A"]))
    assert Primitive.SOURCE_ROUTER in [r.primitive for r in report.results]


def test_parked_node_attributes_to_permission_gate():
    classifier = HAFCClassifier()
    report = classifier.classify(_result(parked_nodes=["gated"]))
    assert any(
        r.primitive == Primitive.PERMISSION_GATE and r.confidence >= 0.9
        for r in report.results
    )


def test_downgraded_claim_attributes_to_critic():
    classifier = HAFCClassifier()
    report = classifier.classify(_result(downgraded_claims=["c1"]))
    assert any(r.primitive == Primitive.CRITIC for r in report.results)


def test_unbound_claim_attributes_to_synthesis():
    classifier = HAFCClassifier()
    claim = Claim(
        text="x",
        evidence_ids=[],
        verified=False,
        verification_note="no evidence bound",
    )
    report = classifier.classify(_result(claims=[claim], faithfulness=0.0))
    assert any(
        r.primitive == Primitive.SYNTHESIS and r.confidence >= 0.9
        for r in report.results
    )


def test_llm_judge_rejection_attributes_to_llm_judge():
    classifier = HAFCClassifier()
    claim = Claim(
        text="x",
        evidence_ids=["e1"],
        verified=False,
        verification_note="llm judge: not supported",
    )
    report = classifier.classify(_result(claims=[claim], faithfulness=0.0))
    assert any(r.primitive == Primitive.LLM_JUDGE for r in report.results)


def test_executable_rejection_attributes_to_executable_verifier():
    classifier = HAFCClassifier()
    claim = Claim(
        text="x",
        evidence_ids=["e1"],
        verified=False,
        verification_note="executable verifier rejected: ratio mismatch",
    )
    report = classifier.classify(_result(claims=[claim], faithfulness=0.0))
    assert any(
        r.primitive == Primitive.EXECUTABLE_VERIFIER and r.confidence >= 0.9
        for r in report.results
    )


def test_mutation_warning_attributes_to_mutation_probe():
    classifier = HAFCClassifier()
    claim = Claim(text="x", evidence_ids=["e1"], verified=False, mutation_warning=True)
    report = classifier.classify(_result(claims=[claim], faithfulness=0.0))
    assert any(r.primitive == Primitive.MUTATION_PROBE for r in report.results)


def test_unclassified_rejection_is_low_confidence_with_alternates():
    classifier = HAFCClassifier()
    claim = Claim(text="x", evidence_ids=["e1"], verified=False, verification_note="mystery fail")
    report = classifier.classify(_result(claims=[claim], faithfulness=0.0))
    results = [r for r in report.results if "mystery" in r.evidence_span]
    assert results
    assert results[0].confidence <= 0.5
    assert len(results[0].alternate_primitives) >= 1


def test_missing_dag_id_attributes_to_planner():
    classifier = HAFCClassifier()
    report = classifier.classify(_result(dag_id=""))
    assert any(r.primitive == Primitive.PLANNER for r in report.results)


def test_top_primitive_returns_highest_confidence():
    classifier = HAFCClassifier()
    claim_high = Claim(
        text="a",
        evidence_ids=[],
        verified=False,
        verification_note="no evidence bound",
    )
    claim_low = Claim(
        text="b",
        evidence_ids=["e"],
        verified=False,
        verification_note="mystery",
    )
    report = classifier.classify(
        _result(claims=[claim_high, claim_low], faithfulness=0.0)
    )
    # no-evidence-bound is ~0.95, mystery is ~0.4 → synthesis wins.
    assert report.top_primitive() == Primitive.SYNTHESIS
