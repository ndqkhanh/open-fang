"""LoopDetector (v7.2) — short-circuit repeated (kind, args) dispatches.

Clean-room from alexgreensh token-optimizer pattern (README only).

The scheduler canonicalizes `(node.kind, sorted(args.items()))` into a hash
key; repeated hashes within a single pipeline run return a cached output.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from ..models import Node


def canonical_key(node: Node) -> str:
    """Stable hash over (kind, args) regardless of dict insertion order."""
    args_canonical = json.dumps(node.args or {}, sort_keys=True, default=str)
    raw = f"{node.kind}||{args_canonical}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class LoopDetector:
    seen: dict[str, Any] = field(default_factory=dict)
    hit_count: int = 0

    def saw_before(self, node: Node) -> bool:
        return canonical_key(node) in self.seen

    def record(self, node: Node, output: Any) -> None:
        self.seen[canonical_key(node)] = output

    def cached_output(self, node: Node) -> Any:
        self.hit_count += 1
        return self.seen.get(canonical_key(node))

    def reset(self) -> None:
        self.seen.clear()
        self.hit_count = 0
