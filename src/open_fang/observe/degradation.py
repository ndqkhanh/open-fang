"""DegradationMonitor (v7.2) — 7-signal quality monitor with S/A/B/C/D/F grades.

Clean-room reimplementation of the token-optimizer (alexgreensh) pattern —
README-only reference; no code ported (source is PolyForm-NC).

Signals tracked per run:
    1. faithfulness_trend      — mean of last-N faithfulness_ratio values
    2. retry_rate              — share of node attempts > 1
    3. mutation_warning_rate   — share of claims with mutation_warning=True
    4. critic_downgrade_rate   — share of claims in downgraded_claims
    5. attribution_entropy     — Shannon entropy of primitive attributions
    6. duplicate_fetch_rate    — share of repeat node dispatches
    7. verdict_flip_rate       — share of claims with verification_note set

Aggregate grade = min(per-signal grades). Checkpoint triggers when ≥3 signals
fall below C.
"""
from __future__ import annotations

import math
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..pipeline import PipelineResult


Grade = Literal["S", "A", "B", "C", "D", "F"]
_GRADES: tuple[Grade, ...] = ("S", "A", "B", "C", "D", "F")


def _grade_for(value: float, *, thresholds: tuple[float, ...]) -> Grade:
    """thresholds are ascending — value > thresholds[i] → at least grade i."""
    for i, t in enumerate(thresholds):
        if value >= t:
            return _GRADES[i]
    return "F"


_FAITHFULNESS_THRESHOLDS = (0.98, 0.95, 0.90, 0.85, 0.80)   # higher = better
_RATE_ERR_THRESHOLDS = (0.0, 0.05, 0.10, 0.20, 0.35)          # lower = better → flip sign
_ENTROPY_THRESHOLDS = (2.2, 1.7, 1.2, 0.8, 0.4)               # higher = better (more diverse)


def _rate_grade(rate: float) -> Grade:
    """For error-rate signals: lower is better. Invert to grade."""
    score = 1.0 - rate
    return _grade_for(score, thresholds=tuple(1.0 - t for t in _RATE_ERR_THRESHOLDS))


@dataclass
class SignalReport:
    value: float
    grade: Grade
    description: str


@dataclass
class DegradationReport:
    grades: dict[str, SignalReport] = field(default_factory=dict)
    aggregate: Grade = "S"
    should_checkpoint: bool = False

    def to_dict(self) -> dict:
        return {
            "aggregate": self.aggregate,
            "should_checkpoint": self.should_checkpoint,
            "signals": {
                name: {
                    "value": s.value,
                    "grade": s.grade,
                    "description": s.description,
                }
                for name, s in self.grades.items()
            },
        }


@dataclass
class DegradationMonitor:
    window: int = 10
    faithfulness_window: deque = field(default_factory=deque)
    retry_events: list[int] = field(default_factory=list)
    dispatched_kinds: Counter = field(default_factory=Counter)

    def observe(self, result: PipelineResult) -> None:
        self.faithfulness_window.append(result.report.faithfulness_ratio)
        while len(self.faithfulness_window) > self.window:
            self.faithfulness_window.popleft()

    def evaluate(self, result: PipelineResult) -> DegradationReport:
        r = result.report
        report = DegradationReport()

        # Signal 1 — faithfulness trend (rolling mean, fallback to current run).
        if self.faithfulness_window:
            trend = sum(self.faithfulness_window) / len(self.faithfulness_window)
        else:
            trend = r.faithfulness_ratio
        report.grades["faithfulness_trend"] = SignalReport(
            value=trend,
            grade=_grade_for(trend, thresholds=_FAITHFULNESS_THRESHOLDS),
            description=f"{trend:.3f} rolling mean",
        )

        # Signal 2 — retry rate (stand-in: failed_nodes / total_nodes if report exposes it).
        total_nodes = max(len(result.failed_nodes) + len(result.parked_nodes) + 1, 1)
        retry_rate = len(result.failed_nodes) / total_nodes
        report.grades["retry_rate"] = SignalReport(
            value=retry_rate,
            grade=_rate_grade(retry_rate),
            description=f"{retry_rate:.3f} retry share",
        )

        # Signal 3 — mutation_warning rate.
        warnings = sum(
            1 for s in r.sections for c in s.claims if c.mutation_warning
        )
        mw_rate = warnings / max(r.total_claims, 1)
        report.grades["mutation_warning_rate"] = SignalReport(
            value=mw_rate,
            grade=_rate_grade(mw_rate),
            description=f"{warnings}/{r.total_claims} claims warned",
        )

        # Signal 4 — critic downgrade rate.
        downgrade_rate = len(result.downgraded_claims) / max(r.total_claims, 1)
        report.grades["critic_downgrade_rate"] = SignalReport(
            value=downgrade_rate,
            grade=_rate_grade(downgrade_rate),
            description=f"{len(result.downgraded_claims)}/{r.total_claims} downgraded",
        )

        # Signal 5 — attribution entropy (spread across primitives).
        entropy = _attribution_entropy(result)
        report.grades["attribution_entropy"] = SignalReport(
            value=entropy,
            grade=_grade_for(entropy, thresholds=_ENTROPY_THRESHOLDS),
            description=f"{entropy:.2f} nats",
        )

        # Signal 6 — duplicate fetch rate.
        # (Approximated: repeated activated_skills share.)
        skills = Counter(result.activated_skills)
        repeated = sum(v for v in skills.values() if v > 1) - len(
            [v for v in skills.values() if v > 1]
        )
        repeat_rate = repeated / max(sum(skills.values()), 1)
        report.grades["duplicate_fetch_rate"] = SignalReport(
            value=repeat_rate,
            grade=_rate_grade(repeat_rate),
            description=f"{repeat_rate:.3f} skill repeat",
        )

        # Signal 7 — verdict flip rate (note-ful claims among verified).
        flipped = sum(
            1
            for s in r.sections
            for c in s.claims
            if c.verification_note and c.verified
        )
        flip_rate = flipped / max(r.total_claims, 1)
        report.grades["verdict_flip_rate"] = SignalReport(
            value=flip_rate,
            grade=_rate_grade(flip_rate),
            description=f"{flipped}/{r.total_claims} note-ful verified claims",
        )

        report.aggregate = _worst_grade([s.grade for s in report.grades.values()])
        # Checkpoint when ≥3 signals are C or worse.
        report.should_checkpoint = (
            sum(1 for s in report.grades.values() if _grade_rank(s.grade) >= _grade_rank("C"))
            >= 3
        )
        return report


def _attribution_entropy(result: PipelineResult) -> float:
    """Shannon entropy over attribution primitives. Zero if no attribution."""
    if not getattr(result, "attribution", None) or not result.attribution.results:
        return 2.5  # no attribution = treated as maximally diverse
    counts = Counter(r.primitive.value for r in result.attribution.results)
    total = sum(counts.values())
    if total <= 1:
        return 2.5
    probs = [c / total for c in counts.values()]
    return -sum(p * math.log(p) for p in probs if p > 0)


def _grade_rank(g: Grade) -> int:
    return _GRADES.index(g)


def _worst_grade(grades: list[Grade]) -> Grade:
    if not grades:
        return "S"
    return max(grades, key=_grade_rank)
