from __future__ import annotations

import pytest

from open_fang.kb.store import KBStore
from open_fang.memory.sandbox import (
    DEFAULT_THRESHOLD_BYTES,
    ToolOutputSandbox,
    payload_size_bytes,
    threshold_from_env,
)
from open_fang.models import Evidence, SourceRef


@pytest.fixture
def kb() -> KBStore:
    return KBStore(db_path=":memory:").open()


def _ev(i: int, content: str = "", *, relevance: float | None = None) -> Evidence:
    rel = relevance if relevance is not None else max(0.0, 1.0 - i * 0.05)
    return Evidence(
        id=f"e{i:04d}",
        source=SourceRef(
            kind="arxiv",
            identifier=f"arxiv:{i:04d}",
            title=f"Paper {i}",
        ),
        content=content or f"Paper {i} content about topic {i}.",
        channel="abstract",
        relevance=rel,
    )


def _large_evidence(n: int, per_item_chars: int = 200) -> list[Evidence]:
    payload = "X" * per_item_chars
    return [_ev(i, content=f"{payload} about topic_{i}") for i in range(n)]


def test_payload_size_bytes_sums_content():
    ev = [_ev(1, content="abc"), _ev(2, content="defgh")]
    assert payload_size_bytes(ev) == 8


def test_should_sandbox_gate_threshold(kb: KBStore):
    sandbox = ToolOutputSandbox(kb, threshold_bytes=100)
    assert sandbox.should_sandbox(_large_evidence(5, per_item_chars=300)) is True
    assert sandbox.should_sandbox([_ev(1, content="tiny")]) is False


def test_sandbox_stores_full_and_returns_top_k(kb: KBStore):
    sandbox = ToolOutputSandbox(kb, threshold_bytes=0)  # always sandbox
    evidence = _large_evidence(50)
    handle, top = sandbox.sandbox(
        evidence=evidence, source_kind="search.arxiv", query="topic_0", top_k=5
    )
    assert len(top) == 5
    # Top 5 ranked by relevance — indices 0-4 have highest.
    top_ids = {e.id for e in top}
    assert "e0000" in top_ids
    assert "e0004" in top_ids
    assert sandbox.count_under(handle) == 50
    # Stats updated.
    assert sandbox.stats.total_sandboxed == 1
    assert sandbox.stats.total_items_stored == 50
    assert sandbox.stats.total_bytes_deferred > 0


def test_retrieve_bm25_finds_matching_item(kb: KBStore):
    sandbox = ToolOutputSandbox(kb, threshold_bytes=0)
    evidence = _large_evidence(30)
    handle, top = sandbox.sandbox(
        evidence=evidence, source_kind="search.arxiv", query="topic_0", top_k=3
    )
    # "topic_27" isn't in the top-3 (relevance-ordered) — must be retrievable via BM25.
    retrieved = sandbox.retrieve(handle, "topic_27", limit=5)
    retrieved_ids = {e.id for e in retrieved}
    assert "e0027" in retrieved_ids


def test_retrieve_empty_query_returns_empty(kb: KBStore):
    sandbox = ToolOutputSandbox(kb, threshold_bytes=0)
    handle, _ = sandbox.sandbox(
        evidence=_large_evidence(10), source_kind="search.arxiv", query="x"
    )
    assert sandbox.retrieve(handle, "") == []
    assert sandbox.retrieve(handle, "   ") == []


def test_retrieve_unknown_handle_returns_empty(kb: KBStore):
    sandbox = ToolOutputSandbox(kb, threshold_bytes=0)
    assert sandbox.retrieve("nonexistent-handle", "topic") == []


def test_get_all_returns_every_item(kb: KBStore):
    sandbox = ToolOutputSandbox(kb, threshold_bytes=0)
    handle, _ = sandbox.sandbox(
        evidence=_large_evidence(7), source_kind="search.arxiv", query="x"
    )
    assert len(sandbox.get_all(handle)) == 7


def test_sandbox_does_not_leak_across_handles(kb: KBStore):
    sandbox = ToolOutputSandbox(kb, threshold_bytes=0)
    h1, _ = sandbox.sandbox(
        evidence=_large_evidence(5), source_kind="search.arxiv", query="a"
    )
    h2, _ = sandbox.sandbox(
        evidence=_large_evidence(5), source_kind="search.arxiv", query="b"
    )
    assert h1 != h2
    # Retrieval is handle-scoped.
    hits_1 = sandbox.retrieve(h1, "topic", limit=20)
    hits_2 = sandbox.retrieve(h2, "topic", limit=20)
    assert len(hits_1) == 5
    assert len(hits_2) == 5


def test_threshold_from_env_fallback(monkeypatch):
    monkeypatch.delenv("OPEN_FANG_SANDBOX_THRESHOLD_BYTES", raising=False)
    assert threshold_from_env() == DEFAULT_THRESHOLD_BYTES
    monkeypatch.setenv("OPEN_FANG_SANDBOX_THRESHOLD_BYTES", "10000")
    assert threshold_from_env() == 10000
    monkeypatch.setenv("OPEN_FANG_SANDBOX_THRESHOLD_BYTES", "not_a_number")
    assert threshold_from_env() == DEFAULT_THRESHOLD_BYTES


def test_constructor_prefers_explicit_threshold_over_env(kb: KBStore, monkeypatch):
    monkeypatch.setenv("OPEN_FANG_SANDBOX_THRESHOLD_BYTES", "99999")
    sandbox = ToolOutputSandbox(kb, threshold_bytes=100)
    assert sandbox.threshold_bytes == 100
