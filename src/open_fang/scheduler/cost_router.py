"""Per-node model selection: cheap vs. strong based on node kind."""
from __future__ import annotations

from ..models import NodeKind

_STRONG_NODES: set[NodeKind] = {
    "synthesize.briefing",
    "verify.claim",
    "compare.papers",
}


def model_for(kind: NodeKind, *, default: str = "cheap") -> str:
    """Return 'strong' for reasoning-heavy nodes, else the default tier."""
    return "strong" if kind in _STRONG_NODES else default
