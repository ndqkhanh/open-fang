"""Weighted random walk over the citation graph.

Edge-kind weights come from v2-plan.md §3.W2 (and SemaClaw-style 3/2/1 tiers):
    cites                    → 3  (strong)
    extends / refutes        → 2  (weak)
    shares-author / same-benchmark / same-technique-family → 1  (independent)
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .store import KBStore

EDGE_WEIGHTS: dict[str, int] = {
    "cites": 3,
    "extends": 2,
    "refutes": 2,
    "shares-author": 1,
    "same-benchmark": 1,
    "same-technique-family": 1,
}


@dataclass
class WalkStep:
    paper_id: str
    arrived_via: str | None  # edge kind taken from the previous step; None on start


def weighted_random_walk(
    kb: KBStore,
    *,
    start: str | None = None,
    hops: int = 3,
    rng: random.Random | None = None,
    prefer_kinds: list[str] | None = None,
) -> list[WalkStep]:
    """Return a list of WalkStep from `start` (default: first KB paper).

    Terminates early if the current node has no outgoing edges. If
    `prefer_kinds` is set, edges whose kind is in the set receive a
    multiplicative boost (x2) over their base weight.
    """
    rng = rng or random.Random(0)
    if start is None:
        ids = kb.list_paper_ids()
        if not ids:
            return []
        start = ids[0]

    if kb.get_paper(start) is None:
        return []

    steps: list[WalkStep] = [WalkStep(paper_id=start, arrived_via=None)]
    visited: set[str] = {start}
    cur = start
    for _ in range(hops):
        out = kb.list_outgoing_edges(cur)
        # Avoid revisiting — keeps walks purposeful in small graphs.
        out = [(dst, kind) for dst, kind in out if dst not in visited]
        if not out:
            break
        weights = [_weight_for(kind, prefer_kinds) for _, kind in out]
        dst, kind = rng.choices(out, weights=weights, k=1)[0]
        steps.append(WalkStep(paper_id=dst, arrived_via=kind))
        visited.add(dst)
        cur = dst
    return steps


def _weight_for(kind: str, prefer_kinds: list[str] | None) -> int:
    w = EDGE_WEIGHTS.get(kind, 1)
    if prefer_kinds and kind in prefer_kinds:
        w *= 2
    return w
