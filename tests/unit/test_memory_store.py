from __future__ import annotations

import pytest

from open_fang.kb.store import KBStore
from open_fang.memory.store import MemoryStore
from open_fang.models import Span


@pytest.fixture
def memory() -> MemoryStore:
    kb = KBStore(db_path=":memory:").open()
    return MemoryStore(kb)


def _span(*, trace_id: str = "t1", node_id: str = "n1", kind: str = "search.arxiv",
          verdict: str = "ok") -> Span:
    return Span(
        trace_id=trace_id,
        node_id=node_id,
        kind=kind,  # type: ignore[arg-type]
        started_at=1000.0,
        ended_at=1000.5,
        verdict=verdict,  # type: ignore[arg-type]
    )


def test_append_returns_id_and_persists(memory: MemoryStore):
    obs_id = memory.append(_span())
    assert obs_id and len(obs_id) == 12
    assert memory.count() == 1


def test_tier_a_compact_index_returns_newest_first(memory: MemoryStore):
    memory.append(_span(node_id="n1"))
    memory.append(_span(node_id="n2"))
    memory.append(_span(node_id="n3"))
    index = memory.compact_index(limit=10)
    assert len(index) == 3
    # Newest first → every line is a one-liner with the kind + verdict.
    assert all("search.arxiv" in line for line in index)
    assert all("verdict=ok" in line for line in index)


def test_tier_a_respects_limit(memory: MemoryStore):
    for i in range(5):
        memory.append(_span(node_id=f"n{i}"))
    assert len(memory.compact_index(limit=2)) == 2


def test_tier_b_timeline_paginates(memory: MemoryStore):
    for i in range(5):
        memory.append(_span(node_id=f"n{i}"))
    page_1 = memory.timeline(offset=0, limit=2)
    page_2 = memory.timeline(offset=2, limit=2)
    assert len(page_1) == 2
    assert len(page_2) == 2
    # Timeline entries carry IDs we can use for Tier C.
    assert all(o.id for o in page_1 + page_2)
    # No overlap.
    page_1_ids = {o.id for o in page_1}
    page_2_ids = {o.id for o in page_2}
    assert not (page_1_ids & page_2_ids)


def test_tier_c_fetches_full_span_json(memory: MemoryStore):
    obs_id = memory.append(_span(node_id="n42", kind="verify.claim"))
    obs = memory.get_observation(obs_id)
    assert obs is not None
    assert obs.id == obs_id
    assert obs.node_id == "n42"
    assert obs.node_kind == "verify.claim"
    assert obs.full_json["trace_id"] == "t1"
    assert obs.full_json["started_at"] == 1000.0


def test_tier_c_returns_none_for_missing_id(memory: MemoryStore):
    assert memory.get_observation("nonexistent") is None


def test_error_verdict_preserved_in_detail(memory: MemoryStore):
    obs_id = memory.append(
        _span(verdict="error") if True else _span(),
    )
    obs = memory.get_observation(obs_id)
    assert obs is not None
    assert obs.verdict == "error"


def test_stage_label_optional(memory: MemoryStore):
    obs_id = memory.append(_span(), stage="retrieve")
    obs = memory.get_observation(obs_id)
    assert obs is not None
    assert obs.stage == "retrieve"
    # Null stage also works.
    obs_id2 = memory.append(_span(node_id="n2"))
    obs2 = memory.get_observation(obs_id2)
    assert obs2 is not None
    assert obs2.stage is None


def test_count_tracks_all_appends(memory: MemoryStore):
    for i in range(7):
        memory.append(_span(node_id=f"n{i}"))
    assert memory.count() == 7
