from __future__ import annotations

import pytest

from open_fang.eval.graph_metrics import (
    GraphBenchReport,
    graph_f1,
    precision_at_k,
    recall_at_k,
    summarize,
)


def test_precision_at_5_all_relevant():
    assert precision_at_k(["a", "b", "c", "d", "e"], {"a", "b", "c", "d", "e"}, k=5) == 1.0


def test_precision_at_5_none_relevant():
    assert precision_at_k(["a", "b"], {"c", "d"}, k=5) == 0.0


def test_precision_respects_k_clamp():
    assert precision_at_k(["a", "b", "c"], {"a", "c"}, k=5) == pytest.approx(2 / 3)


def test_recall_at_5_covers_all():
    assert recall_at_k(["a", "b", "c"], {"a", "b", "c"}, k=5) == 1.0


def test_recall_at_5_partial():
    assert recall_at_k(["a"], {"a", "b"}, k=5) == 0.5


def test_recall_empty_relevant_returns_one():
    assert recall_at_k(["a", "b"], set(), k=5) == 1.0


def test_graph_f1_perfect():
    edges = {("a", "b", "cites")}
    assert graph_f1(edges, edges) == 1.0


def test_graph_f1_disjoint():
    assert graph_f1({("a", "b", "cites")}, {("c", "d", "cites")}) == 0.0


def test_graph_f1_partial_overlap():
    got = {("a", "b", "cites"), ("a", "c", "cites")}
    truth = {("a", "b", "cites"), ("a", "d", "cites")}
    # tp=1, fp=1, fn=1 → P=0.5, R=0.5 → F1=0.5
    assert graph_f1(got, truth) == 0.5


def test_graph_f1_empty_both():
    assert graph_f1(set(), set()) == 1.0


def test_summarize_aggregates():
    per_query = [
        (["a", "b", "c"], {"a", "b"}),      # P@5=2/3, R@5=1.0
        (["x", "y", "z"], {"y", "q"}),      # P@5=1/3, R@5=0.5
    ]
    edges = {("a", "b", "cites")}
    truth = {("a", "b", "cites"), ("c", "d", "cites")}
    report = summarize(per_query, retrieved_edges=edges, ground_truth_edges=truth)
    assert isinstance(report, GraphBenchReport)
    assert report.n_queries == 2
    assert report.precision_at_5 == pytest.approx(0.5)
    assert report.recall_at_5 == pytest.approx(0.75)
    # F1 on edges: tp=1, fp=0, fn=1 → P=1, R=0.5 → F1 = 2*(1*0.5)/(1+0.5) = 0.666...
    assert report.graph_f1 == pytest.approx(2 / 3)


def test_summarize_empty():
    report = summarize([], retrieved_edges=set(), ground_truth_edges=set())
    assert report.n_queries == 0
    assert report.precision_at_5 == 0.0


def test_meets_floor_gates_correctly():
    strong = GraphBenchReport(0.5, 0.9, 0.6, n_queries=20)
    assert strong.meets_floor() is True
    weak = GraphBenchReport(0.3, 0.9, 0.6, n_queries=20)
    assert weak.meets_floor() is False


def test_precision_rejects_invalid_k():
    with pytest.raises(ValueError):
        precision_at_k(["a"], {"a"}, k=0)
