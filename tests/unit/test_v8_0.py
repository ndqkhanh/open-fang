from __future__ import annotations

import pytest

from open_fang.kb.self_wire import InferredEdge, SelfWirer, persist
from open_fang.kb.store import KBStore
from open_fang.models import SourceRef


@pytest.fixture
def seeded_kb() -> KBStore:
    kb = KBStore(db_path=":memory:").open()
    kb.upsert_paper(
        SourceRef(kind="arxiv", identifier="arxiv:2305.18323",
                  title="ReWOO", authors=["Xu"], published_at="2023-05"),
        abstract="ReWOO decouples reasoning from observations.",
    )
    kb.upsert_paper(
        SourceRef(kind="arxiv", identifier="arxiv:2210.03629",
                  title="ReAct", authors=["Yao"], published_at="2022-10"),
        abstract="ReAct interleaves reasoning and acting.",
    )
    kb.upsert_paper(
        SourceRef(kind="arxiv", identifier="arxiv:2303.11366",
                  title="Reflexion", authors=["Shinn"], published_at="2023-03"),
        abstract="Reflexion extracts verbal lessons across episodes.",
    )
    return kb


def test_arxiv_id_pattern_emits_cites_edge(seeded_kb: KBStore):
    wirer = SelfWirer(seeded_kb)
    edges = wirer.process(
        "arxiv:2305.18323",
        "Builds on 2210.03629 and compares to 2303.11366.",
    )
    # Two citations — ReAct + Reflexion.
    kinds = {e.kind for e in edges}
    assert kinds == {"cites"}
    dsts = sorted(e.dst_paper_id for e in edges)
    assert dsts == ["arxiv:2210.03629", "arxiv:2303.11366"]
    assert all(e.confidence >= 0.9 for e in edges)
    assert all(e.pattern_name == "arxiv-id" for e in edges)


def test_self_reference_skipped(seeded_kb: KBStore):
    edges = SelfWirer(seeded_kb).process(
        "arxiv:2305.18323",
        "This paper (2305.18323) proposes ReWOO.",
    )
    assert edges == []


def test_unknown_arxiv_ids_skipped(seeded_kb: KBStore):
    edges = SelfWirer(seeded_kb).process(
        "arxiv:2305.18323",
        "Cites a fictional paper 9999.12345 that isn't in the KB.",
    )
    assert edges == []


def test_author_year_pattern_resolves_known_author(seeded_kb: KBStore):
    edges = SelfWirer(seeded_kb).process(
        "arxiv:2305.18323",
        "Building on prior work (Yao, 2022), we propose...",
    )
    # Yao + 2022 → ReAct.
    assert any(
        e.dst_paper_id == "arxiv:2210.03629" and e.pattern_name == "author-year"
        for e in edges
    )


def test_author_year_with_et_al(seeded_kb: KBStore):
    edges = SelfWirer(seeded_kb).process(
        "arxiv:2305.18323",
        "As (Shinn et al., 2023) showed, verbal reflection helps.",
    )
    assert any(e.dst_paper_id == "arxiv:2303.11366" for e in edges)


def test_dedup_within_single_run(seeded_kb: KBStore):
    edges = SelfWirer(seeded_kb).process(
        "arxiv:2305.18323",
        "2210.03629 2210.03629 (Yao, 2022)",  # same dst via two patterns
    )
    # Unique (src, dst, kind) triples — only one cites edge to ReAct.
    unique_keys = {(e.src_paper_id, e.dst_paper_id, e.kind) for e in edges}
    assert len(unique_keys) == 1
    assert ("arxiv:2305.18323", "arxiv:2210.03629", "cites") in unique_keys


def test_persist_writes_edges_to_kb(seeded_kb: KBStore):
    edges = [
        InferredEdge(
            src_paper_id="arxiv:2305.18323",
            dst_paper_id="arxiv:2210.03629",
            kind="cites",
            confidence=0.95,
            pattern_name="arxiv-id",
        )
    ]
    count = persist(edges, seeded_kb)
    assert count == 1
    stored = seeded_kb.list_edges("arxiv:2305.18323")
    assert ("arxiv:2305.18323", "arxiv:2210.03629", "cites") in stored


def test_empty_content_yields_no_edges(seeded_kb: KBStore):
    assert SelfWirer(seeded_kb).process("arxiv:2305.18323", "") == []
    assert SelfWirer(seeded_kb).process("arxiv:2305.18323", "   ") == []
