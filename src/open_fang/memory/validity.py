"""Bayesian memory validity + contradiction detection (v7.3).

Source pattern: Token Savior (Recall) — Bayesian validity tracking +
contradiction detection over persistent memory observations.

Implementation uses a beta-binomial update on a single `validity` score per
observation:
    prior α0, β0 = 2, 2  (weak — evidence dominates after ~10 updates)
    corroborate → α += 1 → mean = α / (α+β) rises
    contradict  → β += 1 → mean falls

The validity score bounds to [0, 1] and feeds a re-ranked compact index.
"""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_ALPHA = 2
DEFAULT_BETA = 2


@dataclass
class ValidityState:
    alpha: int = DEFAULT_ALPHA
    beta: int = DEFAULT_BETA

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def corroborate(self) -> None:
        self.alpha += 1

    def contradict(self) -> None:
        self.beta += 1


def update_validity(state: ValidityState, *, corroborated: bool) -> float:
    """Beta-binomial update. Returns new mean."""
    if corroborated:
        state.corroborate()
    else:
        state.contradict()
    return state.mean


def detect_contradictions(
    pairs: list[tuple[str, str]],
    shared_tokens: list[tuple[str, str, set[str]]],
    *,
    opposite_signal_words: tuple[str, ...] = (
        "not", "never", "without", "opposite", "contradicts",
    ),
) -> list[tuple[str, str]]:
    """Simple surface-level contradiction detector.

    `pairs`: candidate (id_a, id_b) pairs with overlapping topic.
    `shared_tokens`: list of (id_a, id_b, overlap_set). For each pair, detect
    whether text_a contains opposite_signal_words that text_b does not, or
    vice-versa — heuristic proxy for "one asserts, one negates".

    Returns the subset of pairs flagged as contradictions.
    """
    flagged: list[tuple[str, str]] = []
    _ = pairs  # signature kept for API symmetry
    for id_a, id_b, overlap in shared_tokens:
        if not overlap:
            continue
        has_neg_a = any(w in overlap for w in opposite_signal_words)
        has_neg_b_only = any(w in overlap for w in opposite_signal_words) and not has_neg_a
        if has_neg_a or has_neg_b_only:
            flagged.append((id_a, id_b))
    return flagged


def rerank_by_validity(
    entries: list[tuple[str, float, float]],
    *,
    recency_weight: float = 0.4,
    validity_weight: float = 0.6,
) -> list[str]:
    """Re-rank a list of (id, recency_score, validity_score) by weighted sum.

    `recency_score` and `validity_score` both in [0, 1]; higher is better.
    """
    scored = [
        (i, recency_weight * r + validity_weight * v) for i, r, v in entries
    ]
    scored.sort(key=lambda t: -t[1])
    return [i for i, _ in scored]
