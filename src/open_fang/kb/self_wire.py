"""Zero-LLM self-wiring (v8.0) — GBrain pattern, domain-swapped to papers.

For every paper upserted, scan its content with deterministic regex patterns
and emit typed edges pointing to papers already in the KB. No LLM calls.

Patterns:
    arxiv-id    → cites edge (high confidence)
    bracketed   → [N] references (if a References section is parseable)
    author-year → (Smith et al., 2023) inline cites (weak confidence)
    technique   → shared technique mentions (v8.2 extends this)
    benchmark   → shared benchmark mentions (v8.2 extends this)

All patterns are compiled once at module load. Results include confidence
and pattern_name so downstream can weight + trace.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .store import KBStore


@dataclass(frozen=True)
class InferredEdge:
    src_paper_id: str
    dst_paper_id: str
    kind: str
    confidence: float
    pattern_name: str
    provenance: str = ""

    def to_row(self) -> tuple[str, str, str]:
        return (self.src_paper_id, self.dst_paper_id, self.kind)


# Canonical arxiv id: 4-digit YYMM + '.' + 4-5 digit sequence, optional vN.
_ARXIV_ID_RE = re.compile(r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b")
# Author-year: "(Smith et al., 2023)" or "(Smith, 2023)"
_AUTHOR_YEAR_RE = re.compile(
    r"\(([A-Z][a-zA-Z\-]+)(?:\s+et\s+al\.?)?,\s*(\d{4})\)"
)
# Bracketed reference: "[1]", "[10]" — useful when a References section is present.
_BRACKET_REF_RE = re.compile(r"\[(\d{1,3})\]")


class SelfWirer:
    """Run regex-based extraction on paper content; emit `InferredEdge`s.

    `process(paper_id, content)` is pure: returns inferred edges; the caller
    decides whether to persist them to the `edges` table.
    """

    def __init__(self, kb: KBStore) -> None:
        self.kb = kb
        self._known_ids: set[str] | None = None

    def refresh_known(self) -> None:
        self._known_ids = set(self.kb.list_paper_ids())

    def known(self) -> set[str]:
        if self._known_ids is None:
            self.refresh_known()
        assert self._known_ids is not None
        return self._known_ids

    def process(self, paper_id: str, content: str) -> list[InferredEdge]:
        edges: list[InferredEdge] = []
        known = self.known()

        # Pattern 1: arxiv id → cites (high confidence).
        for match in _ARXIV_ID_RE.finditer(content or ""):
            raw_id = match.group(1)
            dst = f"arxiv:{raw_id}"
            if dst == paper_id:
                continue
            if dst not in known:
                continue
            edges.append(
                InferredEdge(
                    src_paper_id=paper_id,
                    dst_paper_id=dst,
                    kind="cites",
                    confidence=0.95,
                    pattern_name="arxiv-id",
                    provenance="self-wire:arxiv-id",
                )
            )

        # Pattern 2: author-year → cites (medium confidence). The target author
        # is unresolved until a real author-index table lands in v8.2; for
        # v8.0 we record the mention but emit no edge unless a known paper's
        # first-author surname matches.
        for match in _AUTHOR_YEAR_RE.finditer(content or ""):
            author = match.group(1)
            year = match.group(2)
            # Best-effort: look for any known paper whose kind='arxiv' abstract
            # mentions this author+year. Cheap lookup; replaced by v8.2 index.
            resolved = self._resolve_author_year(author, year)
            for dst in resolved:
                if dst == paper_id or dst not in known:
                    continue
                edges.append(
                    InferredEdge(
                        src_paper_id=paper_id,
                        dst_paper_id=dst,
                        kind="cites",
                        confidence=0.55,
                        pattern_name="author-year",
                        provenance="self-wire:author-year",
                    )
                )

        # Pattern 3: bracketed references are too ambiguous without the
        # corresponding References section; surface count only for v8.0.
        bracketed_count = len(_BRACKET_REF_RE.findall(content or ""))
        _ = bracketed_count  # reserved for v8.2 resolver

        # Deduplicate within this run.
        return _dedup(edges)

    def _resolve_author_year(self, author: str, year: str) -> list[str]:
        """Return paper_ids whose `authors` CSV contains `author` AND whose
        `published_at` starts with `year`. Zero-LLM, deterministic SQL."""
        rows = self.kb._c.execute(  # noqa: SLF001
            """
            SELECT id FROM papers
            WHERE authors LIKE ? AND COALESCE(published_at, '') LIKE ?
            """,
            (f"%{author}%", f"{year}%"),
        ).fetchall()
        return [r["id"] for r in rows]


def _dedup(edges: list[InferredEdge]) -> list[InferredEdge]:
    seen: set[tuple[str, str, str]] = set()
    out: list[InferredEdge] = []
    for e in edges:
        key = (e.src_paper_id, e.dst_paper_id, e.kind)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def persist(edges: list[InferredEdge], kb: KBStore) -> int:
    """Insert inferred edges into the KB's `edges` table. Returns count added."""
    added = 0
    for e in edges:
        kb.add_edge(e.src_paper_id, e.dst_paper_id, e.kind)
        added += 1
    return added
