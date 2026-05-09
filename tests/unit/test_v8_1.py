from __future__ import annotations

import pytest

from open_fang.kb.cascades import CascadeEngine
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
    return KBStore(db_path=":memory:").open()


def test_rule1_cites_extends_depends_on(kb: KBStore):
    _seed(kb, ["a", "b", "c"])
    kb.add_edge("a", "b", "cites")
    kb.add_edge("b", "c", "extends")
    out = CascadeEngine(kb)._rule_cites_extends_depends_on()
    assert len(out) == 1
    e = out[0]
    assert e.src_paper_id == "a"
    assert e.dst_paper_id == "c"
    assert e.kind == "depends_on"
    assert e.via_paper_id == "b"


def test_rule2_co_cited(kb: KBStore):
    _seed(kb, ["a", "b", "c"])
    kb.add_edge("a", "b", "cites")
    kb.add_edge("a", "c", "cites")
    out = CascadeEngine(kb)._rule_co_cited()
    assert len(out) == 1
    e = out[0]
    assert {e.src_paper_id, e.dst_paper_id} == {"b", "c"}
    assert e.kind == "co_cited_with"


def test_rule3_shared_author_extends(kb: KBStore):
    _seed(kb, ["a", "b", "c"])
    kb.add_edge("a", "b", "shares-author")
    kb.add_edge("b", "c", "extends")
    out = CascadeEngine(kb)._rule_shared_author_related()
    assert any(
        e.src_paper_id == "a" and e.dst_paper_id == "c" and e.kind == "likely-related-to"
        for e in out
    )


def test_rule4_same_benchmark_transitive(kb: KBStore):
    _seed(kb, ["a", "b", "c"])
    kb.add_edge("a", "b", "same-benchmark")
    kb.add_edge("b", "c", "same-benchmark")
    out = CascadeEngine(kb)._rule_same_benchmark_transitive()
    assert any(
        e.src_paper_id == "a" and e.dst_paper_id == "c" and e.kind == "same-benchmark"
        for e in out
    )


def test_run_all_combines_all_rules(kb: KBStore):
    _seed(kb, ["a", "b", "c", "d"])
    kb.add_edge("a", "b", "cites")
    kb.add_edge("b", "c", "extends")
    kb.add_edge("a", "d", "cites")
    out = CascadeEngine(kb).run_all()
    kinds = {e.kind for e in out}
    assert "depends_on" in kinds        # a depends_on c (via b)
    assert "co_cited_with" in kinds     # b co_cited_with d (via a)


def test_run_all_on_empty_kb(kb: KBStore):
    assert CascadeEngine(kb).run_all() == []


def test_cascades_never_emit_self_loops(kb: KBStore):
    _seed(kb, ["a", "b"])
    kb.add_edge("a", "b", "cites")
    kb.add_edge("b", "a", "extends")
    # a cites b ∧ b extends a would emit depends_on(a, a) — must be skipped.
    out = CascadeEngine(kb)._rule_cites_extends_depends_on()
    assert all(e.src_paper_id != e.dst_paper_id for e in out)


def test_cascade_edge_has_provenance_metadata(kb: KBStore):
    _seed(kb, ["a", "b", "c"])
    kb.add_edge("a", "b", "cites")
    kb.add_edge("b", "c", "extends")
    out = CascadeEngine(kb).run_all()
    assert out
    assert all(e.rule_name and e.via_paper_id for e in out)
