"""Pytest fixtures shared across unit, integration, and evaluation tiers."""
from __future__ import annotations

from pathlib import Path

import pytest

from open_fang.models import Brief, Evidence, SourceRef
from open_fang.sources.mock import MockSource


@pytest.fixture
def brief() -> Brief:
    return Brief(
        question="What is ReWOO and how does it differ from ReAct?",
        max_cost_usd=0.10,
        target_length_words=800,
    )


@pytest.fixture
def canned_evidence() -> list[Evidence]:
    return [
        Evidence(
            id="e1",
            source=SourceRef(
                kind="arxiv",
                identifier="arxiv:2305.18323",
                title="ReWOO: Decoupling Reasoning from Observations",
                authors=["Xu, B."],
                published_at="2023-05",
            ),
            content=(
                "ReWOO decouples reasoning from observations. "
                "The planner emits a DAG of tool calls resolved in parallel."
            ),
            channel="abstract",
            relevance=0.95,
        ),
        Evidence(
            id="e2",
            source=SourceRef(
                kind="arxiv",
                identifier="arxiv:2210.03629",
                title="ReAct: Synergizing Reasoning and Acting",
                authors=["Yao, S."],
                published_at="2022-10",
            ),
            content=(
                "ReAct interleaves reasoning and acting in a single loop. "
                "The agent iterates thought-action-observation turns."
            ),
            channel="abstract",
            relevance=0.92,
        ),
    ]


@pytest.fixture
def mock_source(canned_evidence: list[Evidence]) -> MockSource:
    return MockSource(canned=canned_evidence)


@pytest.fixture
def tmp_fang(tmp_path: Path) -> Path:
    fang = tmp_path / "FANG.md"
    fang.write_text(
        "# FANG seed\n\nDomain: AI agents; evidence bar: arxiv OK.\n",
        encoding="utf-8",
    )
    return fang
