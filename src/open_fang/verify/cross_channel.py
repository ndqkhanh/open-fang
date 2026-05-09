"""Cross-channel verification: claim must agree across abstract/body/table.

Skeleton — ships fully in Phase 3.
"""
from __future__ import annotations

from ..models import Claim, Evidence


def confirms_across_channels(claim: Claim, evidence: list[Evidence]) -> bool:
    """Return True when the claim has supporting evidence in ≥2 distinct channels."""
    channels = {e.channel for e in evidence if e.id in claim.evidence_ids}
    return len(channels) >= 2
