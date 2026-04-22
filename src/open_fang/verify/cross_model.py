"""Cross-model verification (v4.2 + v5.2 — three-mode, gstack `/codex` pattern).

Modes (each returns a different verdict shape):
    review       — pass/fail veto from the secondary family.
    adversarial  — secondary generates counter-example; primary re-evaluates.
    consultation — secondary emits advisory note; no veto.

Secondary provider is any `LLMProvider`; usually a different family from
the primary (Anthropic + OpenAI is the canonical pairing).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from harness_core.messages import Message
from harness_core.models import LLMProvider

from ..models import Claim, Evidence

Mode = Literal["review", "adversarial", "consultation"]


@dataclass
class CrossModelVerdict:
    mode: Mode
    supported: bool | None  # None for consultation mode
    advisory_note: str = ""
    counter_example: str = ""  # only for adversarial mode


_REVIEW_SYSTEM = """You are an independent reviewer from a different model family.
Given a CLAIM and cited EVIDENCE, decide review-gate style: pass or fail.
Return ONLY JSON: {"verdict": "pass" | "fail", "reason": "<short>"}."""

_ADVERSARIAL_SYSTEM = """You are an adversarial reviewer from a different model family.
Given a CLAIM and cited EVIDENCE, try to construct a plausible counter-example
that would invalidate the claim. If you cannot construct one, say so.
Return ONLY JSON: {"counter_example": "<span or 'none'>", "withstands_attack": true|false}."""

_CONSULTATION_SYSTEM = """You are a second-opinion consultant from a different model family.
Given a CLAIM and cited EVIDENCE, offer an advisory note for the synthesizer.
Do not veto. Return ONLY JSON: {"note": "<advisory text>"}."""


class CrossModelVerifier:
    """Run a secondary LLM for review / adversarial / consultation verdicts."""

    def __init__(self, *, secondary: LLMProvider) -> None:
        self.secondary = secondary

    def verdict(
        self,
        claim: Claim,
        evidence: list[Evidence],
        *,
        mode: Mode = "review",
    ) -> CrossModelVerdict:
        contents = [e.content for e in evidence if e.id in claim.evidence_ids]
        if mode == "review":
            return self._review(claim.text, contents)
        if mode == "adversarial":
            return self._adversarial(claim.text, contents)
        if mode == "consultation":
            return self._consultation(claim.text, contents)
        raise ValueError(f"unknown mode: {mode!r}")

    def _review(self, claim_text: str, contents: list[str]) -> CrossModelVerdict:
        raw = self._ask(_REVIEW_SYSTEM, claim_text, contents)
        try:
            data = json.loads(raw)
            passed = str(data.get("verdict", "")).lower() == "pass"
        except (json.JSONDecodeError, TypeError):
            passed = "pass" in raw.lower() and "fail" not in raw.lower()
        return CrossModelVerdict(
            mode="review",
            supported=passed,
            advisory_note=raw[:200],
        )

    def _adversarial(self, claim_text: str, contents: list[str]) -> CrossModelVerdict:
        raw = self._ask(_ADVERSARIAL_SYSTEM, claim_text, contents)
        try:
            data = json.loads(raw)
            withstood = bool(data.get("withstands_attack", False))
            counter = str(data.get("counter_example", ""))
        except (json.JSONDecodeError, TypeError):
            withstood = True  # conservative default: if unparseable, claim stands
            counter = ""
        return CrossModelVerdict(
            mode="adversarial",
            supported=withstood,
            counter_example=counter,
            advisory_note=raw[:200],
        )

    def _consultation(self, claim_text: str, contents: list[str]) -> CrossModelVerdict:
        raw = self._ask(_CONSULTATION_SYSTEM, claim_text, contents)
        try:
            data = json.loads(raw)
            note = str(data.get("note", raw))
        except (json.JSONDecodeError, TypeError):
            note = raw
        return CrossModelVerdict(
            mode="consultation",
            supported=None,  # advisory only
            advisory_note=note[:500],
        )

    def _ask(self, system: str, claim: str, contents: list[str]) -> str:
        evidence_block = "\n---\n".join(f"[evidence {i + 1}] {c}" for i, c in enumerate(contents))
        reply = self.secondary.generate(
            messages=[
                Message.system(system),
                Message.user(
                    f"CLAIM:\n{claim}\n\nEVIDENCE:\n{evidence_block}\n\nEmit the JSON now."
                ),
            ],
            max_tokens=300,
            temperature=0.0,
        )
        return (reply.content or "").strip()
