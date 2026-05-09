from __future__ import annotations

import pytest

from open_fang.kb.reconciler import (
    ensure_provenance_column,
    reconcile_self_wired_edges,
)
from open_fang.kb.self_wire import InferredEdge
from open_fang.kb.store import KBStore
from open_fang.models import SourceRef


def _seed(kb: KBStore, ids: list[str]) -> None:
    for pid in ids:
        kb.upsert_paper(
            SourceRef(kind="arxiv", identifier=pid, title=pid, authors=["X"]),
            abstract=f"{pid}.",
        )


@pytest.fixture
def kb() -> KBStore:
    kb = KBStore(db_path=":memory:").open()
    _seed(kb, ["a", "b", "c", "d"])
    return kb


def _edge(src: str, dst: str, *, provenance: str = "self-wire:arxiv-id") -> InferredEdge:
    return InferredEdge(
        src_paper_id=src,
        dst_paper_id=dst,
        kind="cites",
        confidence=0.9,
        pattern_name="arxiv-id",
        provenance=provenance,
    )


def test_ensure_provenance_column_idempotent(kb: KBStore):
    ensure_provenance_column(kb)
    ensure_provenance_column(kb)  # second call no-ops
    cols = [
        r["name"]
        for r in kb._c.execute("PRAGMA table_info(edges)").fetchall()  # noqa: SLF001
    ]
    assert "provenance" in cols


def test_first_reconcile_adds_all_edges(kb: KBStore):
    report = reconcile_self_wired_edges(
        kb, paper_id="a", new_edges=[_edge("a", "b"), _edge("a", "c")],
    )
    assert report.added == 2
    assert report.removed == 0
    assert report.kept == 0


def test_second_reconcile_with_identical_edges_is_noop(kb: KBStore):
    edges = [_edge("a", "b"), _edge("a", "c")]
    reconcile_self_wired_edges(kb, paper_id="a", new_edges=edges)
    report = reconcile_self_wired_edges(kb, paper_id="a", new_edges=edges)
    assert report.added == 0
    assert report.removed == 0
    assert report.kept == 2


def test_reconcile_removes_stale_and_adds_new(kb: KBStore):
    reconcile_self_wired_edges(
        kb, paper_id="a", new_edges=[_edge("a", "b"), _edge("a", "c")],
    )
    report = reconcile_self_wired_edges(
        kb, paper_id="a", new_edges=[_edge("a", "b"), _edge("a", "d")],
    )
    assert report.added == 1      # d
    assert report.removed == 1    # c
    assert report.kept == 1       # b
    edges_in_kb = kb.list_outgoing_edges("a")
    dst_set = {dst for dst, _ in edges_in_kb}
    assert dst_set == {"b", "d"}


def test_manual_edge_survives_reconcile(kb: KBStore):
    ensure_provenance_column(kb)
    # Add a manual edge directly (no self-wire provenance).
    kb._c.execute(  # noqa: SLF001
        "INSERT INTO edges (src_paper_id, dst_paper_id, kind, provenance) VALUES (?, ?, ?, ?)",
        ("a", "b", "extends", "manual"),
    )
    kb._c.commit()  # noqa: SLF001

    report = reconcile_self_wired_edges(
        kb, paper_id="a",
        new_edges=[_edge("a", "c")],  # the extends-b manual edge not in new set
    )
    assert report.preserved_manual >= 1
    # Manual edge still present.
    outgoing = kb.list_outgoing_edges("a")
    assert ("b", "extends") in outgoing
    # New self-wire edge added.
    assert ("c", "cites") in outgoing


def test_reconcile_preserves_null_provenance_as_manual(kb: KBStore):
    ensure_provenance_column(kb)
    # Pre-v8 edges have NULL provenance — treated as manual.
    kb.add_edge("a", "b", "cites")  # NULL provenance
    report = reconcile_self_wired_edges(
        kb, paper_id="a", new_edges=[_edge("a", "c")],
    )
    assert report.preserved_manual >= 1
    outgoing = kb.list_outgoing_edges("a")
    assert ("b", "cites") in outgoing
