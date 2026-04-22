"""Graph-retrieval metrics (v8.5) — OpenFang's BrainBench-analog.

GBrain publishes Precision@5 / Recall@5 / Graph-F1 on a 240-page corpus.
v8.5 gives OpenFang the same shape on our own curated corpus. This module
provides the math; the corpus + tests live in tests/fixtures and
tests/evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass


def precision_at_k(retrieved: list[str], relevant: set[str], *, k: int = 5) -> float:
    if k <= 0:
        raise ValueError("k must be >= 1")
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for item in top_k if item in relevant)
    return hits / len(top_k)


def recall_at_k(retrieved: list[str], relevant: set[str], *, k: int = 5) -> float:
    if k <= 0:
        raise ValueError("k must be >= 1")
    if not relevant:
        return 1.0  # nothing to recall → trivially satisfied
    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / len(relevant)


def graph_f1(
    retrieved_edges: set[tuple[str, str, str]],
    ground_truth_edges: set[tuple[str, str, str]],
) -> float:
    if not retrieved_edges and not ground_truth_edges:
        return 1.0
    if not retrieved_edges or not ground_truth_edges:
        return 0.0
    tp = len(retrieved_edges & ground_truth_edges)
    fp = len(retrieved_edges - ground_truth_edges)
    fn = len(ground_truth_edges - retrieved_edges)
    if tp == 0:
        return 0.0
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    return 2 * precision * recall / (precision + recall)


@dataclass
class GraphBenchReport:
    precision_at_5: float
    recall_at_5: float
    graph_f1: float
    n_queries: int

    def meets_floor(self, *, p5: float = 0.40, r5: float = 0.80, f1: float = 0.50) -> bool:
        return (
            self.precision_at_5 >= p5
            and self.recall_at_5 >= r5
            and self.graph_f1 >= f1
        )


def summarize(
    per_query_results: list[tuple[list[str], set[str]]],
    *,
    retrieved_edges: set[tuple[str, str, str]],
    ground_truth_edges: set[tuple[str, str, str]],
) -> GraphBenchReport:
    if not per_query_results:
        return GraphBenchReport(0.0, 0.0, 0.0, 0)
    ps = [precision_at_k(r, rel) for r, rel in per_query_results]
    rs = [recall_at_k(r, rel) for r, rel in per_query_results]
    return GraphBenchReport(
        precision_at_5=sum(ps) / len(ps),
        recall_at_5=sum(rs) / len(rs),
        graph_f1=graph_f1(retrieved_edges, ground_truth_edges),
        n_queries=len(per_query_results),
    )
