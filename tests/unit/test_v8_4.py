from __future__ import annotations

import pytest

from open_fang.kb.backlink import BacklinkIndex, backlink_rank_list
from open_fang.kb.store import KBStore
from open_fang.models import SourceRef


def _seed(kb: KBStore, ids: list[str]) -> None:
    for pid in ids:
        kb.upsert_paper(
            SourceRef(kind="arxiv", identifier=pid, title=pid, authors=["X"]),
            abstract=f"{pid} abstract.",
        )


@pytest.fixture
def kb() -> KBStore:
    kb = KBStore(db_path=":memory:").open()
    _seed(kb, ["a", "b", "c", "d"])
    # b has 3 inbound, c has 1, d has 0.
    kb.add_edge("a", "b", "cites")
    kb.add_edge("c", "b", "cites")
    kb.add_edge("d", "b", "extends")
    kb.add_edge("a", "c", "cites")
    return kb


def test_index_refresh_counts_inbound(kb: KBStore):
    idx = BacklinkIndex()
    idx.refresh(kb)
    assert idx.count_for("b") == 3
    assert idx.count_for("c") == 1
    assert idx.count_for("d") == 0
    assert idx.count_for("nonexistent") == 0


def test_rank_list_sorts_desc(kb: KBStore):
    results = backlink_rank_list(kb, limit=10)
    ids = [e.source.identifier for e in results]
    assert ids[0] == "b"  # highest backlink count
    # c (1) ahead of a and d (both 0).
    assert ids.index("c") < ids.index("d")


def test_rank_list_respects_candidate_filter(kb: KBStore):
    results = backlink_rank_list(kb, candidate_ids=["a", "c"])
    ids = [e.source.identifier for e in results]
    assert set(ids) == {"a", "c"}


def test_rank_list_stable_order_on_ties(kb: KBStore):
    # Add two more zero-count papers; tie-break by id ascending.
    _seed(kb, ["z1", "z0"])
    results = backlink_rank_list(kb, candidate_ids=["z1", "z0"])
    ids = [e.source.identifier for e in results]
    assert ids == ["z0", "z1"]


def test_rank_list_relevance_carries_count(kb: KBStore):
    results = backlink_rank_list(kb, limit=10)
    b = next(e for e in results if e.source.identifier == "b")
    assert b.relevance == 3.0


def test_rank_list_channel_marked(kb: KBStore):
    results = backlink_rank_list(kb, limit=10)
    assert all(e.channel == "backlink-rank" for e in results)


def test_empty_kb_returns_empty():
    kb = KBStore(db_path=":memory:").open()
    assert backlink_rank_list(kb) == []
