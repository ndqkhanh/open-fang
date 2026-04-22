"""Typed-edge pattern cascades (v8.1, depth-1 only).

Pattern source: GBrain's "CEO of X → works_at" inference. Domain-swapped to
papers:
    R1: A cites B ∧ B extends C      ⇒ A depends_on C   (weak, conf 0.4)
    R2: A cites B ∧ A cites C        ⇒ B co_cited_with C (weak, conf 0.5)
    R3: A shares-author B ∧ B extends C ⇒ A likely-related-to C (conf 0.3)
    R4: A same-benchmark-as B ∧ B same-benchmark-as C ⇒ A same-benchmark-as C (conf 0.6)

Cascades run at depth-1 only to avoid edge explosion. Only high-confidence
base edges (confidence ≥ 0.6 in the self-wire output) feed cascades — lower
confidence edges are ignored.
"""
from __future__ import annotations

from dataclasses import dataclass

from .store import KBStore


@dataclass(frozen=True)
class CascadeEdge:
    src_paper_id: str
    dst_paper_id: str
    kind: str
    confidence: float
    rule_name: str
    via_paper_id: str  # the bridge paper that triggered the cascade

    def to_row(self) -> tuple[str, str, str]:
        return (self.src_paper_id, self.dst_paper_id, self.kind)


class CascadeEngine:
    """Apply depth-1 cascade rules over the KB's existing edges table."""

    def __init__(self, kb: KBStore) -> None:
        self.kb = kb

    def run_all(self) -> list[CascadeEdge]:
        edges: list[CascadeEdge] = []
        edges.extend(self._rule_cites_extends_depends_on())
        edges.extend(self._rule_co_cited())
        edges.extend(self._rule_shared_author_related())
        edges.extend(self._rule_same_benchmark_transitive())
        return _dedup(edges)

    # ------------------------------------------------------------- rule 1

    def _rule_cites_extends_depends_on(self) -> list[CascadeEdge]:
        """A cites B ∧ B extends C ⇒ A depends_on C."""
        rows = self.kb._c.execute(  # noqa: SLF001
            """
            SELECT e1.src_paper_id AS a, e1.dst_paper_id AS b, e2.dst_paper_id AS c
            FROM edges e1
            JOIN edges e2 ON e1.dst_paper_id = e2.src_paper_id
            WHERE e1.kind = 'cites' AND e2.kind = 'extends'
              AND e1.src_paper_id != e2.dst_paper_id
            """
        ).fetchall()
        return [
            CascadeEdge(
                src_paper_id=row["a"],
                dst_paper_id=row["c"],
                kind="depends_on",
                confidence=0.4,
                rule_name="cites-extends-depends_on",
                via_paper_id=row["b"],
            )
            for row in rows
        ]

    # ------------------------------------------------------------- rule 2

    def _rule_co_cited(self) -> list[CascadeEdge]:
        """A cites B ∧ A cites C ⇒ B co_cited_with C (for all B != C)."""
        rows = self.kb._c.execute(  # noqa: SLF001
            """
            SELECT e1.dst_paper_id AS b, e2.dst_paper_id AS c, e1.src_paper_id AS a
            FROM edges e1
            JOIN edges e2 ON e1.src_paper_id = e2.src_paper_id
            WHERE e1.kind = 'cites' AND e2.kind = 'cites'
              AND e1.dst_paper_id < e2.dst_paper_id
            """
        ).fetchall()
        return [
            CascadeEdge(
                src_paper_id=row["b"],
                dst_paper_id=row["c"],
                kind="co_cited_with",
                confidence=0.5,
                rule_name="co-cited",
                via_paper_id=row["a"],
            )
            for row in rows
        ]

    # ------------------------------------------------------------- rule 3

    def _rule_shared_author_related(self) -> list[CascadeEdge]:
        """A shares-author B ∧ B extends C ⇒ A likely-related-to C."""
        rows = self.kb._c.execute(  # noqa: SLF001
            """
            SELECT e1.src_paper_id AS a, e1.dst_paper_id AS b, e2.dst_paper_id AS c
            FROM edges e1
            JOIN edges e2 ON e1.dst_paper_id = e2.src_paper_id
            WHERE e1.kind = 'shares-author' AND e2.kind = 'extends'
              AND e1.src_paper_id != e2.dst_paper_id
            """
        ).fetchall()
        return [
            CascadeEdge(
                src_paper_id=row["a"],
                dst_paper_id=row["c"],
                kind="likely-related-to",
                confidence=0.3,
                rule_name="shared-author-extends",
                via_paper_id=row["b"],
            )
            for row in rows
        ]

    # ------------------------------------------------------------- rule 4

    def _rule_same_benchmark_transitive(self) -> list[CascadeEdge]:
        """A same-benchmark B ∧ B same-benchmark C ⇒ A same-benchmark C."""
        rows = self.kb._c.execute(  # noqa: SLF001
            """
            SELECT e1.src_paper_id AS a, e1.dst_paper_id AS b, e2.dst_paper_id AS c
            FROM edges e1
            JOIN edges e2 ON e1.dst_paper_id = e2.src_paper_id
            WHERE e1.kind = 'same-benchmark' AND e2.kind = 'same-benchmark'
              AND e1.src_paper_id != e2.dst_paper_id
            """
        ).fetchall()
        return [
            CascadeEdge(
                src_paper_id=row["a"],
                dst_paper_id=row["c"],
                kind="same-benchmark",
                confidence=0.6,
                rule_name="same-benchmark-transitive",
                via_paper_id=row["b"],
            )
            for row in rows
        ]


def _dedup(edges: list[CascadeEdge]) -> list[CascadeEdge]:
    seen: set[tuple[str, str, str]] = set()
    out: list[CascadeEdge] = []
    for e in edges:
        key = (e.src_paper_id, e.dst_paper_id, e.kind)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out
