"""HybridSearch (v7.1) — BM25 × dense embeddings × RRF × optional reranker.

Clean-room adoption of QMD (tobi/qmd) + claude-context (zilliztech):
    1. BM25 via existing KBStore.search() — FTS5-backed, cheap.
    2. Dense cosine similarity over the `papers_embeddings` sidecar.
    3. Reciprocal Rank Fusion merges the two rank lists with k=60 (QMD default).
    4. Optional: small-LLM reranker pass on the top-30 fused candidates.

Back-compat: when `embedder=None`, HybridSearch degrades to BM25-only — same
output shape as the existing KBStore.search(). Adding an Embedder is the sole
enabler for dense + RRF paths.

Embeddings are populated lazily: `HybridSearch.embed_pending(kb)` walks every
paper that lacks an embedding row and generates one. Pipeline does not block
on missing embeddings — missing rows are silently skipped.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Callable

from ..models import Evidence
from .embedders import Embedder, cosine, pack_vector, unpack_vector
from .store import KBStore

RRF_K = 60  # QMD default; dampens top-rank dominance


@dataclass
class HybridStats:
    bm25_hits: int = 0
    dense_hits: int = 0
    fused: int = 0
    reranked: int = 0


class HybridSearch:
    def __init__(
        self,
        kb: KBStore,
        *,
        embedder: Embedder | None = None,
        reranker: Callable[[str, list[Evidence]], list[Evidence]] | None = None,
        rrf_k: int = RRF_K,
    ) -> None:
        self._kb = kb
        self.embedder = embedder
        self.reranker = reranker
        self.rrf_k = rrf_k
        self.stats = HybridStats()

    @property
    def _c(self):  # noqa: ANN201
        return self._kb._c  # noqa: SLF001 — shared connection

    # ------------------------------------------------------------- embedding

    def embed_and_store(self, paper_id: str, text: str) -> None:
        if self.embedder is None:
            return
        vec = self.embedder.embed(text)
        now = _dt.datetime.utcnow().isoformat(timespec="seconds")
        self._c.execute(
            """
            INSERT OR REPLACE INTO papers_embeddings
              (paper_id, embedding, dim, model_id, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (paper_id, pack_vector(vec), len(vec), self.embedder.model_id, now),
        )
        self._c.commit()

    def embed_pending(self, *, limit: int | None = None) -> int:
        """Generate embeddings for papers missing them. Returns count written."""
        if self.embedder is None:
            return 0
        rows = self._c.execute(
            """
            SELECT p.id, p.title, p.abstract
            FROM papers p
            LEFT JOIN papers_embeddings e ON e.paper_id = p.id
            WHERE e.paper_id IS NULL
            """
            + (f"LIMIT {int(limit)}" if limit else "")
        ).fetchall()
        count = 0
        for r in rows:
            text = " ".join(filter(None, [r["title"], r["abstract"]]))
            self.embed_and_store(r["id"], text)
            count += 1
        return count

    # ------------------------------------------------------------- retrieval

    def search(self, query: str, *, limit: int = 5) -> list[Evidence]:
        bm25_results = self._kb.search(query, limit=limit * 3)
        self.stats.bm25_hits = len(bm25_results)
        if self.embedder is None:
            return bm25_results[:limit]

        dense_results = self._dense_search(query, limit=limit * 3)
        self.stats.dense_hits = len(dense_results)

        fused = _rrf_fuse([bm25_results, dense_results], k=self.rrf_k)
        self.stats.fused = len(fused)

        top = fused[: max(30, limit)]
        if self.reranker is not None and len(top) > 1:
            top = self.reranker(query, top)
            self.stats.reranked = len(top)

        return top[:limit]

    def _dense_search(self, query: str, *, limit: int) -> list[Evidence]:
        assert self.embedder is not None
        query_vec = self.embedder.embed(query)
        rows = self._c.execute(
            """
            SELECT p.id, p.kind, p.title, p.abstract, p.authors, p.published_at,
                   e.embedding, e.dim
            FROM papers p
            JOIN papers_embeddings e ON e.paper_id = p.id
            WHERE e.model_id = ?
            """,
            (self.embedder.model_id,),
        ).fetchall()
        scored: list[tuple[float, Evidence]] = []
        for r in rows:
            vec = unpack_vector(r["embedding"], int(r["dim"]))
            sim = cosine(query_vec, vec)
            if sim <= 0.0:
                continue
            from ..models import SourceRef

            ev = Evidence(
                source=SourceRef(
                    kind=r["kind"] or "kb",
                    identifier=r["id"],
                    title=r["title"] or "",
                    authors=(r["authors"] or "").split(",") if r["authors"] else [],
                    published_at=r["published_at"],
                ),
                content=r["abstract"] or "",
                channel="kb-cache",
                relevance=sim,
            )
            scored.append((sim, ev))
        scored.sort(key=lambda t: -t[0])
        return [ev for _, ev in scored[:limit]]


# ----------------------------------------------------------------- helpers


def _rrf_fuse(rank_lists: list[list[Evidence]], *, k: int = RRF_K) -> list[Evidence]:
    """Merge rank lists via Reciprocal Rank Fusion.

    rrf(d) = Σ 1 / (k + rank_l(d))   for each list l
    """
    scores: dict[str, float] = {}
    first_seen: dict[str, Evidence] = {}
    for results in rank_lists:
        for rank, ev in enumerate(results, start=1):
            key = ev.source.identifier or ev.id
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            first_seen.setdefault(key, ev)
    ordered = sorted(first_seen.values(), key=lambda ev: -scores[ev.source.identifier or ev.id])
    return ordered


__all__ = ["HybridSearch", "HybridStats", "_rrf_fuse", "RRF_K"]
