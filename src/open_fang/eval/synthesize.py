"""MultiHopBriefSynthesizer: generate multi-paper research briefs from citation-graph walks.

Each synthesized brief is a `(Brief, list[Evidence])` pair. The evidence list
is the walk's paper set so the pipeline can treat it as canned input. A brief
that fails to produce ≥ 1 verifiable claim per paper in the walk is filtered
out before return.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from ..kb.random_walk import WalkStep, weighted_random_walk
from ..kb.store import KBStore
from ..models import Brief, Evidence


@dataclass
class SynthesizedBrief:
    brief: Brief
    evidence: list[Evidence]
    walk: list[WalkStep]


class MultiHopBriefSynthesizer:
    def __init__(self, kb: KBStore) -> None:
        self.kb = kb

    def synthesize(
        self,
        n: int,
        *,
        hops: int = 2,
        rng: random.Random | None = None,
        prefer_kinds: list[str] | None = None,
    ) -> list[SynthesizedBrief]:
        rng = rng or random.Random(0)
        paper_ids = self.kb.list_paper_ids()
        if len(paper_ids) < 2:
            return []
        seen_signatures: set[tuple[str, ...]] = set()
        out: list[SynthesizedBrief] = []
        attempts = 0
        max_attempts = max(20, n * 5)
        while len(out) < n and attempts < max_attempts:
            attempts += 1
            start = rng.choice(paper_ids)
            walk = weighted_random_walk(
                self.kb, start=start, hops=hops, rng=rng, prefer_kinds=prefer_kinds
            )
            if len(walk) < 2:
                continue
            signature = tuple(step.paper_id for step in walk)
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            papers = [self.kb.get_paper(step.paper_id) for step in walk]
            evidence = [p for p in papers if p is not None]
            if len(evidence) < 2:
                continue

            brief = _render_brief(walk, evidence)
            out.append(SynthesizedBrief(brief=brief, evidence=evidence, walk=walk))
        return out


def _render_brief(walk: list[WalkStep], evidence: list[Evidence]) -> Brief:
    titles = [e.source.title or e.source.identifier for e in evidence]
    relations: list[str] = []
    for step in walk[1:]:
        if step.arrived_via:
            relations.append(step.arrived_via)
    if relations:
        rel_text = " via " + ", ".join(relations)
    else:
        rel_text = ""
    question = (
        "Compare and connect: "
        + " → ".join(titles)
        + rel_text
        + ". Highlight how each paper relates to the next."
    )
    return Brief(question=question, target_length_words=800)
