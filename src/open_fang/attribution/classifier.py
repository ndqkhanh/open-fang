"""HAFC-lite: rules-first failure-attribution classifier.

Input: PipelineResult. Output: AttributionReport listing
`(primitive, confidence, evidence_span)` tuples for every failure signal.
Low-confidence attributions explicitly mark "multiple primitives possible".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .primitives import Primitive

if TYPE_CHECKING:
    from ..pipeline import PipelineResult


@dataclass
class AttributionResult:
    primitive: Primitive
    confidence: float  # 0.0-1.0
    evidence_span: str
    alternate_primitives: tuple[Primitive, ...] = field(default_factory=tuple)


@dataclass
class AttributionReport:
    results: list[AttributionResult] = field(default_factory=list)
    total_failures: int = 0

    def top_primitive(self) -> Primitive | None:
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.confidence).primitive


class HAFCClassifier:
    """Rules-first classifier. 12 primitives, one rule per primitive minimum."""

    def classify(self, result: PipelineResult) -> AttributionReport:
        report = AttributionReport()
        r = result.report

        # --- Rule 1: failed nodes attribute to scheduler-dispatch or source-router.
        for node_id in result.failed_nodes:
            primitive = Primitive.SOURCE_ROUTER
            evidence = f"failed node {node_id!r}"
            alternates = (Primitive.SCHEDULER_DISPATCH, Primitive.PERMISSION_GATE)
            report.results.append(
                AttributionResult(
                    primitive=primitive,
                    confidence=0.7,
                    evidence_span=evidence,
                    alternate_primitives=alternates,
                )
            )
            report.total_failures += 1

        # --- Rule 2: parked nodes attribute to permission-gate.
        for node_id in result.parked_nodes:
            report.results.append(
                AttributionResult(
                    primitive=Primitive.PERMISSION_GATE,
                    confidence=0.95,
                    evidence_span=f"parked node {node_id!r}",
                )
            )

        # --- Rule 3: downgraded claims (v3.2) attribute to critic.
        for claim_id in result.downgraded_claims:
            report.results.append(
                AttributionResult(
                    primitive=Primitive.CRITIC,
                    confidence=0.9,
                    evidence_span=f"claim {claim_id!r} downgraded by critic",
                )
            )
            report.total_failures += 1

        # --- Claim-level rules (iterate over report sections).
        for section in r.sections:
            for claim in section.claims:
                if claim.verified:
                    continue
                note = (claim.verification_note or "").lower()
                if "no evidence bound" in note:
                    report.results.append(
                        AttributionResult(
                            primitive=Primitive.SYNTHESIS,
                            confidence=0.95,
                            evidence_span=f"claim {claim.id}: {claim.verification_note}",
                        )
                    )
                elif "not found" in note:
                    report.results.append(
                        AttributionResult(
                            primitive=Primitive.SYNTHESIS,
                            confidence=0.85,
                            evidence_span=f"claim {claim.id}: {claim.verification_note}",
                            alternate_primitives=(Primitive.KB_LOOKUP,),
                        )
                    )
                elif "lexical overlap" in note:
                    report.results.append(
                        AttributionResult(
                            primitive=Primitive.SYNTHESIS,
                            confidence=0.7,
                            evidence_span=f"claim {claim.id}: {claim.verification_note}",
                            alternate_primitives=(Primitive.LLM_JUDGE,),
                        )
                    )
                elif "llm judge" in note:
                    report.results.append(
                        AttributionResult(
                            primitive=Primitive.LLM_JUDGE,
                            confidence=0.9,
                            evidence_span=f"claim {claim.id}: {claim.verification_note}",
                        )
                    )
                elif "executable verifier" in note:
                    report.results.append(
                        AttributionResult(
                            primitive=Primitive.EXECUTABLE_VERIFIER,
                            confidence=0.95,
                            evidence_span=f"claim {claim.id}: {claim.verification_note}",
                        )
                    )
                elif claim.mutation_warning:
                    report.results.append(
                        AttributionResult(
                            primitive=Primitive.MUTATION_PROBE,
                            confidence=0.8,
                            evidence_span=f"claim {claim.id}: mutation_warning set",
                        )
                    )
                else:
                    report.results.append(
                        AttributionResult(
                            primitive=Primitive.SYNTHESIS,
                            confidence=0.4,
                            evidence_span=(
                                f"claim {claim.id}: unclassified rejection — "
                                f"note={claim.verification_note!r}"
                            ),
                            alternate_primitives=(
                                Primitive.LLM_JUDGE,
                                Primitive.CRITIC,
                            ),
                        )
                    )
                report.total_failures += 1

        # --- Rule 4: zero activated skills on a degraded-faithfulness run.
        # Only emit when the run has ANY failure signal already; otherwise the
        # rule mis-attributes clean runs with empty activated_skills.
        if (
            hasattr(result, "activated_skills")
            and result.activated_skills == []
            and r.brief.question
            and (
                r.faithfulness_ratio < 0.9
                or result.failed_nodes
                or result.parked_nodes
            )
            and not report.results
        ):
            report.results.append(
                AttributionResult(
                    primitive=Primitive.SKILL_ACTIVATION,
                    confidence=0.3,
                    evidence_span="no skills activated on non-empty brief",
                    alternate_primitives=(Primitive.PLANNER,),
                )
            )

        # --- Rule 5: planner produced no plan at all → planner primitive.
        if not r.dag_id:
            report.results.append(
                AttributionResult(
                    primitive=Primitive.PLANNER,
                    confidence=0.9,
                    evidence_span="no DAG id on result (planner did not emit a plan)",
                )
            )
            report.total_failures += 1

        return report
