from __future__ import annotations

import pytest

from open_fang.kb.embedders import (
    HashEmbedder,
    cosine,
    pack_vector,
    unpack_vector,
)
from open_fang.kb.hybrid_search import HybridSearch, _rrf_fuse
from open_fang.kb.store import KBStore
from open_fang.models import Evidence, SourceRef

# -------- Embedder tests


def test_hash_embedder_is_deterministic_across_instances():
    a = HashEmbedder(dim=32).embed("rewoo decouples reasoning")
    b = HashEmbedder(dim=32).embed("rewoo decouples reasoning")
    assert a == b


def test_hash_embedder_empty_text_returns_zero_vector():
    vec = HashEmbedder(dim=16).embed("")
    assert vec == [0.0] * 16


def test_hash_embedder_distinguishes_texts():
    a = HashEmbedder(dim=64).embed("rewoo")
    b = HashEmbedder(dim=64).embed("reflexion")
    assert a != b


def test_hash_embedder_is_l2_normalized():
    vec = HashEmbedder(dim=32).embed("rewoo paper about decoupling reasoning")
    norm = sum(v * v for v in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_pack_unpack_round_trip():
    vec = [0.1, -0.5, 0.7, 0.0, -1.0]
    blob = pack_vector(vec)
    out = unpack_vector(blob, dim=5)
    assert all(abs(a - b) < 1e-6 for a, b in zip(vec, out))


def test_cosine_of_identical_vectors_is_one():
    v = [0.5, 0.5, 0.5, 0.5]
    assert abs(cosine(v, v) - 1.0) < 1e-6


def test_cosine_of_orthogonal_vectors_is_zero():
    assert abs(cosine([1.0, 0.0], [0.0, 1.0])) < 1e-6


def test_cosine_rejects_dimension_mismatch():
    with pytest.raises(ValueError):
        cosine([1.0, 0.0], [1.0, 0.0, 0.0])


# -------- RRF tests


def _ev(identifier: str) -> Evidence:
    return Evidence(
        source=SourceRef(kind="arxiv", identifier=identifier, title=identifier),
        content="",
    )


def test_rrf_single_list_preserves_order():
    lst = [_ev("a"), _ev("b"), _ev("c")]
    out = _rrf_fuse([lst])
    assert [e.source.identifier for e in out] == ["a", "b", "c"]


def test_rrf_merges_duplicates_with_summed_score():
    # a ranks 1 in both lists → score = 2 * 1/(60+1) = 0.0328
    # b ranks 2 in list1, missing in list2 → score = 1/(60+2) = 0.0161
    # c only in list2 at rank 2 → 0.0161
    lst1 = [_ev("a"), _ev("b")]
    lst2 = [_ev("a"), _ev("c")]
    out = _rrf_fuse([lst1, lst2])
    assert out[0].source.identifier == "a"


def test_rrf_disjoint_lists_produce_union_sorted_by_rank():
    lst1 = [_ev("a"), _ev("b")]
    lst2 = [_ev("c"), _ev("d")]
    out = _rrf_fuse([lst1, lst2])
    ids = {e.source.identifier for e in out}
    assert ids == {"a", "b", "c", "d"}
    # Rank-1 entries (a, c) beat rank-2 entries (b, d).
    assert out[0].source.identifier in {"a", "c"}
    assert out[1].source.identifier in {"a", "c"}


# -------- HybridSearch tests


def _seed(kb: KBStore, entries: list[tuple[str, str, str]]) -> None:
    for aid, title, abstract in entries:
        kb.upsert_paper(
            SourceRef(kind="arxiv", identifier=aid, title=title, authors=["X"]),
            abstract=abstract,
        )


@pytest.fixture
def kb() -> KBStore:
    kb = KBStore(db_path=":memory:").open()
    _seed(
        kb,
        [
            ("arxiv:rewoo", "ReWOO", "Decouples reasoning from observations via a DAG."),
            ("arxiv:react", "ReAct", "Interleaves reasoning and acting in a single loop."),
            ("arxiv:reflexion", "Reflexion", "Extracts verbal lessons across episodes."),
            ("arxiv:voyager", "Voyager", "Lifelong skill library for open-ended learning."),
        ],
    )
    return kb


def test_hybrid_with_no_embedder_falls_back_to_bm25(kb: KBStore):
    hs = HybridSearch(kb, embedder=None)
    results = hs.search("rewoo", limit=2)
    assert results
    assert any(e.source.identifier == "arxiv:rewoo" for e in results)


def test_embed_pending_populates_only_missing_rows(kb: KBStore):
    hs = HybridSearch(kb, embedder=HashEmbedder(dim=32))
    # First call — every paper gets an embedding.
    first = hs.embed_pending()
    assert first == 4
    # Second call — everything already has an embedding.
    assert hs.embed_pending() == 0


def test_hybrid_returns_union_of_bm25_and_dense(kb: KBStore):
    hs = HybridSearch(kb, embedder=HashEmbedder(dim=32))
    hs.embed_pending()
    results = hs.search("reasoning", limit=4)
    ids = [e.source.identifier for e in results]
    # BM25 matches rewoo + react on "reasoning".
    # Dense (HashEmbedder) matches on shared tokens.
    assert "arxiv:rewoo" in ids or "arxiv:react" in ids


def test_hybrid_reranker_is_invoked_when_wired(kb: KBStore):
    hs = HybridSearch(kb, embedder=HashEmbedder(dim=32))
    hs.embed_pending()

    calls: list[int] = []

    def reranker(query: str, items: list[Evidence]) -> list[Evidence]:  # noqa: ARG001
        calls.append(len(items))
        return list(reversed(items))  # deterministic transform

    hs.reranker = reranker
    results = hs.search("reasoning", limit=3)
    assert calls, "reranker was not invoked"
    assert hs.stats.reranked > 0
    assert len(results) <= 3


def test_hybrid_stats_accumulate(kb: KBStore):
    hs = HybridSearch(kb, embedder=HashEmbedder(dim=32))
    hs.embed_pending()
    hs.search("rewoo", limit=3)
    assert hs.stats.bm25_hits > 0
    assert hs.stats.fused > 0
