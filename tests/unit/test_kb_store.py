from __future__ import annotations

import pytest

from open_fang.kb.store import KBStore
from open_fang.models import SourceRef


@pytest.fixture
def kb() -> KBStore:
    return KBStore(db_path=":memory:").open()


def _source(ident: str, title: str, authors: list[str]) -> SourceRef:
    return SourceRef(kind="arxiv", identifier=ident, title=title, authors=authors, published_at="2023")


def test_upsert_paper_is_idempotent(kb: KBStore):
    s = _source("arxiv:1", "ReWOO", ["Xu"])
    kb.upsert_paper(s, abstract="Decoupling reasoning from observations.")
    kb.upsert_paper(s, abstract="Decoupling reasoning from observations (v2).")
    assert kb.count_papers() == 1


def test_add_claim_links_to_paper(kb: KBStore):
    s = _source("arxiv:1", "ReWOO", ["Xu"])
    kb.upsert_paper(s, abstract="Decoupling reasoning from observations.")
    cid = kb.add_claim(paper_id=s.identifier, text="ReWOO decouples reasoning.", verified=True)
    assert cid
    assert kb.count_claims() == 1


def test_fts_search_returns_relevant_paper(kb: KBStore):
    s1 = _source("arxiv:1", "ReWOO: Decoupling Reasoning from Observations", ["Xu"])
    s2 = _source("arxiv:2", "Database Indexing Primer", ["Other"])
    kb.upsert_paper(s1, abstract="ReWOO decouples reasoning from observations.")
    kb.upsert_paper(s2, abstract="B-trees, LSM-trees, and hash indexes compared.")

    hits = kb.search("rewoo reasoning", limit=5)
    assert len(hits) >= 1
    assert hits[0].source.identifier == "arxiv:1"
    assert hits[0].channel == "kb-cache"


def test_fts_search_returns_empty_for_blank_query(kb: KBStore):
    kb.upsert_paper(_source("arxiv:1", "x", []), abstract="y")
    assert kb.search("   ") == []


def test_add_and_list_edges(kb: KBStore):
    s1 = _source("arxiv:a", "A", [])
    s2 = _source("arxiv:b", "B", [])
    kb.upsert_paper(s1, abstract="x")
    kb.upsert_paper(s2, abstract="y")
    kb.add_edge("arxiv:a", "arxiv:b", "cites")
    kb.add_edge("arxiv:a", "arxiv:b", "cites")  # dup ignored

    edges = kb.list_edges("arxiv:a")
    assert edges == [("arxiv:a", "arxiv:b", "cites")]


def test_search_tokenizes_query_safely(kb: KBStore):
    kb.upsert_paper(_source("arxiv:1", "Tree of Thoughts", []), abstract="ToT backtracking lookahead.")
    # Apostrophes in user queries must not break FTS.
    hits = kb.search("tree's thoughts")
    assert len(hits) >= 1
    assert hits[0].source.identifier == "arxiv:1"
