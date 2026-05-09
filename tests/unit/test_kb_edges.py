from __future__ import annotations

import pytest

from open_fang.kb.edges import EdgeExtractor
from open_fang.kb.store import KBStore
from open_fang.models import SourceRef


@pytest.fixture
def kb_with_papers() -> KBStore:
    kb = KBStore(db_path=":memory:").open()
    for aid, title in [
        ("arxiv:2305.18323", "ReWOO"),
        ("arxiv:2210.03629", "ReAct"),
        ("arxiv:2303.11366", "Reflexion"),
    ]:
        kb.upsert_paper(
            SourceRef(kind="arxiv", identifier=aid, title=title, authors=["X"]),
            abstract=f"{title} abstract body.",
        )
    return kb


def test_edge_extractor_detects_known_arxiv_id(kb_with_papers: KBStore):
    extractor = EdgeExtractor(kb_with_papers)
    content = (
        "We build on ReAct (2210.03629) and Reflexion (2303.11366v2). "
        "See also an unknown-paper id 9999.99999."
    )
    result = extractor.extract_from_content("arxiv:2305.18323", content)
    assert result.added == 2
    assert result.skipped_unknown == 1
    edges = kb_with_papers.list_outgoing_edges("arxiv:2305.18323")
    assert sorted(edges) == sorted(
        [("arxiv:2210.03629", "cites"), ("arxiv:2303.11366", "cites")]
    )


def test_edge_extractor_skips_self_reference(kb_with_papers: KBStore):
    extractor = EdgeExtractor(kb_with_papers)
    result = extractor.extract_from_content(
        "arxiv:2305.18323",
        "This paper (2305.18323) builds on prior work.",
    )
    assert result.added == 0
    assert result.skipped_self == 1


def test_extract_for_all_papers_returns_per_paper_result(kb_with_papers: KBStore):
    # Seed cross-references in the abstracts so extraction finds edges.
    kb_with_papers.upsert_paper(
        SourceRef(
            kind="arxiv",
            identifier="arxiv:2305.18323",
            title="ReWOO",
            authors=["X"],
        ),
        abstract="ReWOO extends ReAct 2210.03629 design.",
    )
    extractor = EdgeExtractor(kb_with_papers)
    results = extractor.extract_for_all_papers()
    assert set(results.keys()) == {"arxiv:2305.18323", "arxiv:2210.03629", "arxiv:2303.11366"}
    assert results["arxiv:2305.18323"].added == 1


def test_extract_handles_empty_content(kb_with_papers: KBStore):
    result = EdgeExtractor(kb_with_papers).extract_from_content("arxiv:2305.18323", "")
    assert result.added == 0
    assert result.skipped_self == 0
    assert result.skipped_unknown == 0
