from __future__ import annotations

from open_fang.memory.validity import (
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    ValidityState,
    detect_contradictions,
    rerank_by_validity,
    update_validity,
)


def test_initial_validity_is_prior_mean():
    s = ValidityState()
    assert s.mean == DEFAULT_ALPHA / (DEFAULT_ALPHA + DEFAULT_BETA)
    assert s.mean == 0.5


def test_corroboration_trends_up():
    s = ValidityState()
    for _ in range(5):
        update_validity(s, corroborated=True)
    assert s.mean > 0.7


def test_contradiction_trends_down():
    s = ValidityState()
    for _ in range(5):
        update_validity(s, corroborated=False)
    assert s.mean < 0.3


def test_mixed_evidence_balances():
    s = ValidityState()
    for _ in range(5):
        update_validity(s, corroborated=True)
    for _ in range(5):
        update_validity(s, corroborated=False)
    # After 5 corroborations + 5 contradictions from a (2,2) prior → (7, 7)
    assert abs(s.mean - 0.5) < 1e-6


def test_detect_contradictions_flags_negated_pair():
    pairs = [("a", "b")]
    shared = [("a", "b", {"rewoo", "not", "decouples"})]
    out = detect_contradictions(pairs, shared)
    assert out == [("a", "b")]


def test_detect_contradictions_ignores_overlap_without_negation():
    pairs = [("a", "b")]
    shared = [("a", "b", {"rewoo", "decouples", "reasoning"})]
    assert detect_contradictions(pairs, shared) == []


def test_rerank_respects_validity_over_recency():
    # Older-but-high-validity should outrank newer-but-low-validity.
    entries = [
        ("old_good", 0.1, 0.95),    # old (low recency) + high validity
        ("new_bad", 0.95, 0.10),    # new + low validity
    ]
    order = rerank_by_validity(entries)
    # With default weights (recency=0.4, validity=0.6):
    #   old_good: 0.4*0.1 + 0.6*0.95 = 0.61
    #   new_bad:  0.4*0.95 + 0.6*0.10 = 0.44
    assert order[0] == "old_good"


def test_rerank_recency_dominates_when_weighted():
    entries = [
        ("old_good", 0.1, 0.95),
        ("new_bad", 0.95, 0.10),
    ]
    order = rerank_by_validity(entries, recency_weight=0.9, validity_weight=0.1)
    #   old_good: 0.9*0.1 + 0.1*0.95 = 0.185
    #   new_bad:  0.9*0.95 + 0.1*0.10 = 0.865
    assert order[0] == "new_bad"
