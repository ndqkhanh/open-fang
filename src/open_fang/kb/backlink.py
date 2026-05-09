"""Backlink ranking (v8.4) — GBrain pattern for KB-native PageRank-lite.

Pattern source: GBrain's "well-connected entities rank higher in search".
Applied to papers: a paper with many incoming `cites` edges is ranked
higher, all else equal.

The `BacklinkIndex` caches `backlink_count_by_paper` as a dict and refreshes
on demand (`refresh()`); consumers should refresh after KB mutations.

Exported helper `backlink_rank_list(kb, ids, limit)` returns a ranked
`list[Evidence]` suitable as a third input to the v7.1 RRF fusion in
`HybridSearch`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Evidence, SourceRef
from .store import KBStore


@dataclass
class BacklinkIndex:
    counts: dict[str, int] = field(default_factory=dict)

    def refresh(self, kb: KBStore) -> None:
        rows = kb._c.execute(  # noqa: SLF001
            """
            SELECT dst_paper_id, COUNT(*) AS n
            FROM edges
            GROUP BY dst_paper_id
            """
        ).fetchall()
        self.counts = {r["dst_paper_id"]: int(r["n"]) for r in rows}

    def count_for(self, paper_id: str) -> int:
        return self.counts.get(paper_id, 0)


def backlink_rank_list(
    kb: KBStore,
    *,
    candidate_ids: list[str] | None = None,
    limit: int = 10,
) -> list[Evidence]:
    """Return papers sorted by incoming-edge count (desc).

    If `candidate_ids` is given, the result is filtered to that subset (useful
    for RRF fusion where we want the backlink rank only over candidates that
    survived BM25 or dense search).
    """
    index = BacklinkIndex()
    index.refresh(kb)

    if candidate_ids is not None:
        candidates = [pid for pid in candidate_ids if pid in kb.list_paper_ids()]
    else:
        candidates = kb.list_paper_ids()

    scored = sorted(
        candidates,
        key=lambda pid: (-index.count_for(pid), pid),
    )[:limit]

    results: list[Evidence] = []
    for pid in scored:
        ev = kb.get_paper(pid)
        if ev is not None:
            # Decorate with backlink count in relevance so callers can inspect.
            results.append(
                Evidence(
                    source=SourceRef(
                        kind=ev.source.kind,
                        identifier=ev.source.identifier,
                        title=ev.source.title,
                        authors=ev.source.authors,
                        published_at=ev.source.published_at,
                    ),
                    content=ev.content,
                    channel="backlink-rank",
                    relevance=float(index.count_for(pid)),
                )
            )
    return results
