from __future__ import annotations

import random

import pytest

from open_fang.kb.random_walk import EDGE_WEIGHTS, weighted_random_walk
from open_fang.kb.store import KBStore
from open_fang.models import SourceRef


def _seed_chain(kb: KBStore) -> None:
    for aid in ["arxiv:a", "arxiv:b", "arxiv:c", "arxiv:d"]:
        kb.upsert_paper(
            SourceRef(kind="arxiv", identifier=aid, title=aid, authors=[]),
            abstract=f"{aid} abstract.",
        )
    kb.add_edge("arxiv:a", "arxiv:b", "cites")
    kb.add_edge("arxiv:b", "arxiv:c", "cites")
    kb.add_edge("arxiv:c", "arxiv:d", "cites")


@pytest.fixture
def chain_kb() -> KBStore:
    kb = KBStore(db_path=":memory:").open()
    _seed_chain(kb)
    return kb


def test_walk_follows_chain(chain_kb: KBStore):
    walk = weighted_random_walk(chain_kb, start="arxiv:a", hops=3, rng=random.Random(1))
    assert [s.paper_id for s in walk] == ["arxiv:a", "arxiv:b", "arxiv:c", "arxiv:d"]
    # First step has no arrived_via; subsequent steps report edge kind.
    assert walk[0].arrived_via is None
    assert all(s.arrived_via == "cites" for s in walk[1:])


def test_walk_terminates_at_dead_end(chain_kb: KBStore):
    walk = weighted_random_walk(chain_kb, start="arxiv:d", hops=5, rng=random.Random(0))
    assert len(walk) == 1  # no outgoing edges


def test_walk_on_empty_kb():
    kb = KBStore(db_path=":memory:").open()
    assert weighted_random_walk(kb, hops=3) == []


def test_walk_with_missing_start_returns_empty(chain_kb: KBStore):
    assert weighted_random_walk(chain_kb, start="arxiv:missing", hops=3) == []


def test_walk_avoids_revisiting_nodes():
    kb = KBStore(db_path=":memory:").open()
    for aid in ["arxiv:a", "arxiv:b"]:
        kb.upsert_paper(SourceRef(kind="arxiv", identifier=aid, title=aid), abstract=aid)
    # Cycle a<->b
    kb.add_edge("arxiv:a", "arxiv:b", "cites")
    kb.add_edge("arxiv:b", "arxiv:a", "cites")
    walk = weighted_random_walk(kb, start="arxiv:a", hops=5, rng=random.Random(0))
    # Only two distinct nodes; walk terminates at step 2 since a already visited.
    assert [s.paper_id for s in walk] == ["arxiv:a", "arxiv:b"]


def test_edge_weight_table_is_complete():
    """Every edge kind declared in the plan has a weight."""
    from open_fang.kb.graph import EDGE_KINDS

    for kind in EDGE_KINDS:
        assert kind in EDGE_WEIGHTS, f"EDGE_WEIGHTS missing weight for {kind!r}"


def test_prefer_kinds_biases_walk():
    kb = KBStore(db_path=":memory:").open()
    for aid in ["s", "a", "b"]:
        kb.upsert_paper(
            SourceRef(kind="arxiv", identifier=f"arxiv:{aid}", title=aid), abstract=aid
        )
    # s has two outgoing edges to a (shares-author, weight 1) and b (same-benchmark, weight 1).
    kb.add_edge("arxiv:s", "arxiv:a", "shares-author")
    kb.add_edge("arxiv:s", "arxiv:b", "same-benchmark")

    # With preference on shares-author, boosted weight picks 'a' far more often.
    picks = []
    for seed in range(100):
        walk = weighted_random_walk(
            kb,
            start="arxiv:s",
            hops=1,
            rng=random.Random(seed),
            prefer_kinds=["shares-author"],
        )
        if len(walk) >= 2:
            picks.append(walk[1].paper_id)
    # Under the 2x boost, shares-author wins roughly 2/3. Assert a loose bound.
    assert picks.count("arxiv:a") > picks.count("arxiv:b")
