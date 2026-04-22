from __future__ import annotations

import pytest

from open_fang.kb.graph import build_subgraph
from open_fang.kb.store import KBStore
from open_fang.models import SourceRef


@pytest.fixture
def linked_kb() -> KBStore:
    kb = KBStore(db_path=":memory:").open()
    for aid, title in [
        ("arxiv:rewoo", "ReWOO"),
        ("arxiv:react", "ReAct"),
        ("arxiv:reflexion", "Reflexion"),
        ("arxiv:voyager", "Voyager"),
        ("arxiv:isolated", "Lone Paper"),
    ]:
        kb.upsert_paper(
            SourceRef(kind="arxiv", identifier=aid, title=title, authors=["A"]),
            abstract=f"{title} abstract.",
        )
    kb.add_edge("arxiv:rewoo", "arxiv:react", "extends")
    kb.add_edge("arxiv:reflexion", "arxiv:react", "extends")
    kb.add_edge("arxiv:voyager", "arxiv:react", "cites")
    kb.add_edge("arxiv:voyager", "arxiv:reflexion", "cites")
    return kb


def test_subgraph_returns_seed_and_direct_neighbors(linked_kb: KBStore):
    g = build_subgraph(linked_kb, seed_id="arxiv:rewoo", depth=1)
    ids = sorted(n.id for n in g.nodes)
    assert ids == ["arxiv:react", "arxiv:rewoo"]
    assert len(g.edges) == 1
    assert g.edges[0].kind == "extends"


def test_subgraph_depth_two_pulls_second_hop(linked_kb: KBStore):
    g = build_subgraph(linked_kb, seed_id="arxiv:voyager", depth=2, direction="out")
    ids = sorted(n.id for n in g.nodes)
    # direction='out' follows outgoing edges only, so we don't walk into rewoo
    # via react's incoming edges.
    assert "arxiv:voyager" in ids
    assert "arxiv:react" in ids
    assert "arxiv:reflexion" in ids
    assert "arxiv:rewoo" not in ids
    assert "arxiv:isolated" not in ids


def test_subgraph_direction_both_reaches_inbound_neighbors(linked_kb: KBStore):
    """With direction='both', the walk can reverse edges, so voyager→react
    exposes rewoo→react at depth 2."""
    g = build_subgraph(linked_kb, seed_id="arxiv:voyager", depth=2, direction="both")
    ids = sorted(n.id for n in g.nodes)
    assert "arxiv:rewoo" in ids  # reachable via react's incoming edge from rewoo


def test_subgraph_isolated_seed_yields_singleton(linked_kb: KBStore):
    g = build_subgraph(linked_kb, seed_id="arxiv:isolated", depth=3)
    assert [n.id for n in g.nodes] == ["arxiv:isolated"]
    assert g.edges == []


def test_subgraph_missing_seed_returns_empty(linked_kb: KBStore):
    g = build_subgraph(linked_kb, seed_id="arxiv:does-not-exist", depth=2)
    assert g.nodes == []
    assert g.edges == []
    assert g.seed_id is None


def test_subgraph_query_resolves_seed_via_fts(linked_kb: KBStore):
    g = build_subgraph(linked_kb, query="rewoo", depth=1)
    assert g.seed_id == "arxiv:rewoo"
    ids = sorted(n.id for n in g.nodes)
    assert "arxiv:rewoo" in ids


def test_subgraph_to_dict_is_cytoscape_shaped(linked_kb: KBStore):
    payload = build_subgraph(linked_kb, seed_id="arxiv:rewoo", depth=1).to_dict()
    assert set(payload.keys()) == {"seed_id", "depth", "nodes", "edges"}
    for node in payload["nodes"]:
        assert "data" in node
        assert "id" in node["data"] and "label" in node["data"]
    for edge in payload["edges"]:
        assert "data" in edge
        assert "source" in edge["data"] and "target" in edge["data"]
        assert edge["data"]["kind"] in {
            "cites", "extends", "refutes", "shares-author",
            "same-benchmark", "same-technique-family",
        }


def test_subgraph_respects_max_nodes(linked_kb: KBStore):
    g = build_subgraph(linked_kb, seed_id="arxiv:voyager", depth=5, max_nodes=2)
    assert len(g.nodes) <= 2


def test_subgraph_empty_kb_returns_empty():
    kb = KBStore(db_path=":memory:").open()
    g = build_subgraph(kb, query="anything", depth=2)
    assert g.nodes == [] and g.edges == []


def test_subgraph_no_seed_no_query_returns_empty(linked_kb: KBStore):
    g = build_subgraph(linked_kb, depth=2)
    assert g.nodes == [] and g.edges == []
    assert g.seed_id is None
