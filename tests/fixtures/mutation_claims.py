"""Hand-authored quantitative claims + evidence for v2.4 mutation-resistance eval.

Each entry is a (claim_text, is_fabricated) pair sharing the same evidence
pool. The resistance test runs every claim through the full 5-tier verifier
and asserts the fabricated ones get caught (via Tier 2 warning + Tier 3
rejection + Tier 4 executable when a script is provided).

The `structured_data` on the evidence gives executable Tier 4 material to
work with.
"""
from __future__ import annotations

from dataclasses import dataclass

from open_fang.models import Evidence, SourceRef


@dataclass
class MutationCase:
    claim_text: str
    is_fabricated: bool
    script: str | None = None


EVIDENCE = Evidence(
    id="fixture-ev",
    source=SourceRef(kind="arxiv", identifier="arxiv:rewoo", title="ReWOO"),
    content=(
        "ReWOO reduces token usage fivefold relative to ReAct on multi-hop benchmarks. "
        "It improves throughput by 47% and reduces latency from 2.4s to 0.8s per query. "
        "The approach always decouples reasoning from observations and never interleaves "
        "planning with execution."
    ),
    channel="abstract",
    structured_data={
        "rewoo_tokens_per_query": 120,
        "react_tokens_per_query": 600,
        "throughput_gain_pct": 47.0,
        "react_latency_s": 2.4,
        "rewoo_latency_s": 0.8,
    },
)


CASES: list[MutationCase] = [
    # Honest claims — should be verified.
    MutationCase(
        claim_text="ReWOO reduces token usage fivefold relative to ReAct on multi-hop benchmarks.",
        is_fabricated=False,
        script=(
            "r = evidence['react_tokens_per_query'] / evidence['rewoo_tokens_per_query']\n"
            "assert 4.0 <= r <= 6.0"
        ),
    ),
    MutationCase(
        claim_text="ReWOO improves throughput by 47% over ReAct.",
        is_fabricated=False,
        script="assert abs(evidence['throughput_gain_pct'] - 47.0) < 0.5",
    ),
    MutationCase(
        claim_text="ReWOO reduces latency from 2.4s to 0.8s per query.",
        is_fabricated=False,
        script=(
            "assert abs(evidence['react_latency_s'] - 2.4) < 0.01\n"
            "assert abs(evidence['rewoo_latency_s'] - 0.8) < 0.01"
        ),
    ),
    MutationCase(
        claim_text="ReWOO always decouples reasoning from observations.",
        is_fabricated=False,
    ),
    # Fabricated numeric claims — should be caught by Tier 4 (executable) or Tier 2.
    MutationCase(
        claim_text="ReWOO reduces token usage tenfold relative to ReAct on multi-hop benchmarks.",
        is_fabricated=True,
        script=(
            "r = evidence['react_tokens_per_query'] / evidence['rewoo_tokens_per_query']\n"
            "assert 9.0 <= r <= 11.0, 'tenfold not supported'"
        ),
    ),
    MutationCase(
        claim_text="ReWOO improves throughput by 470% over ReAct.",
        is_fabricated=True,
        script="assert abs(evidence['throughput_gain_pct'] - 470.0) < 0.5",
    ),
    MutationCase(
        claim_text="ReWOO increases latency from 0.8s to 2.4s per query.",
        is_fabricated=True,
        script=(
            "assert evidence['rewoo_latency_s'] > evidence['react_latency_s'], "
            "'claim says ReWOO is slower, but evidence shows the opposite'"
        ),
    ),
    MutationCase(
        claim_text="ReWOO never decouples reasoning from observations.",
        is_fabricated=True,
    ),
    MutationCase(
        claim_text="ReWOO reduces token usage by 50 points relative to ReAct.",
        is_fabricated=True,
        script=(
            "# claim said 'points' (absolute) but evidence supports 'fold' (ratio);\n"
            "# evidence has no 50-point delta support.\n"
            "diff = evidence['react_tokens_per_query'] - evidence['rewoo_tokens_per_query']\n"
            "assert diff == 50, 'evidence shows %d token delta, not 50' % diff"
        ),
    ),
    MutationCase(
        claim_text="ReWOO reduces latency from 2.4s to 8.0s per query.",
        is_fabricated=True,
        script="assert abs(evidence['rewoo_latency_s'] - 8.0) < 0.01",
    ),
]
