"""Delta-mode for source re-reads (v7.4).

Pattern source: alexgreensh token-optimizer (README only, clean-room).

When a source adapter returns Evidence for a paper already in the KB with an
identical content hash, we emit a `DeltaStub` — a lightweight Evidence-shaped
record with `content=''`, `delta_handle=<paper_id>`, and `delta_mode=True`.
The pipeline can fetch the real content from KB on demand; context stays lean.
"""
from __future__ import annotations

import hashlib

from ..kb.store import KBStore
from ..models import Evidence


def content_sha256(content: str) -> str:
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()[:16]


def delta_stub(ev: Evidence) -> Evidence:
    """Return a zero-content stub referencing the evidence's source id."""
    return ev.model_copy(
        update={
            "content": "",
            "delta_mode": True,
            "delta_handle": ev.source.identifier,
        }
    )


def apply_delta_mode(
    evidence: list[Evidence],
    *,
    kb: KBStore,
    known_hashes: dict[str, str] | None = None,
) -> tuple[list[Evidence], list[str]]:
    """For each evidence whose source is already in KB with matching hash,
    replace with a DeltaStub. Returns (transformed_list, delta_ids)."""
    delta_ids: list[str] = []
    if known_hashes is None:
        known_hashes = _load_known_hashes(kb)
    out: list[Evidence] = []
    for ev in evidence:
        paper_id = ev.source.identifier
        incoming = content_sha256(ev.content)
        existing = known_hashes.get(paper_id)
        if existing is not None and existing == incoming:
            out.append(delta_stub(ev))
            delta_ids.append(paper_id)
        else:
            out.append(ev)
    return out, delta_ids


def resolve_delta(ev: Evidence, kb: KBStore) -> Evidence | None:
    """Fetch the full content for a delta-stub via KB lookup."""
    if not ev.delta_mode or not ev.delta_handle:
        return None
    return kb.get_paper(ev.delta_handle)


def _load_known_hashes(kb: KBStore) -> dict[str, str]:
    rows = kb._c.execute("SELECT id, abstract FROM papers").fetchall()  # noqa: SLF001
    return {r["id"]: content_sha256(r["abstract"] or "") for r in rows}
