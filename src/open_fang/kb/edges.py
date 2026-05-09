"""EdgeExtractor: scan paper content for references to other KB papers.

v2.2 MVP — `cites` edges only, detected via arxiv-id regex against the set of
KB paper identifiers. v2.3 will upgrade edges to `extends / refutes /
same-technique-family` via LLM classification of reference context.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .store import KBStore

# Canonical arxiv id pattern: 4-digit YYMM + '.' + 4-5 digit sequence, optional vN.
_ARXIV_ID_RE = re.compile(r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b")


VALID_EDGE_KINDS = (
    "cites",
    "extends",
    "refutes",
    "shares-author",
    "same-benchmark",
    "same-technique-family",
)


@dataclass
class ExtractionResult:
    added: int = 0
    skipped_self: int = 0
    skipped_unknown: int = 0


class EdgeExtractor:
    """Given a source paper's id + content, add 'cites' edges to KB papers
    referenced by arxiv id."""

    def __init__(self, kb: KBStore) -> None:
        self.kb = kb
        self._known_ids: set[str] | None = None

    def extract_from_content(self, src_paper_id: str, content: str) -> ExtractionResult:
        known = self._known()
        matches = {m.group(1) for m in _ARXIV_ID_RE.finditer(content or "")}
        result = ExtractionResult()
        for raw_id in matches:
            dst = f"arxiv:{raw_id}"
            if dst == src_paper_id:
                result.skipped_self += 1
                continue
            if dst not in known:
                result.skipped_unknown += 1
                continue
            self.kb.add_edge(src_paper_id, dst, "cites")
            result.added += 1
        # After mutating the graph, refresh our known-ids cache in case new
        # papers landed via upsert between calls.
        self._known_ids = None
        return result

    def extract_for_all_papers(self) -> dict[str, ExtractionResult]:
        """Convenience: scan every paper's abstract for outgoing 'cites' edges."""
        out: dict[str, ExtractionResult] = {}
        for paper_id in self.kb.list_paper_ids():
            ev = self.kb.get_paper(paper_id)
            if ev is None:
                continue
            out[paper_id] = self.extract_from_content(paper_id, ev.content)
        return out

    def _known(self) -> set[str]:
        if self._known_ids is None:
            self._known_ids = set(self.kb.list_paper_ids())
        return self._known_ids
