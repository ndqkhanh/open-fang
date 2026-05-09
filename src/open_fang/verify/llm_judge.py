"""LLM-judge claim verifier.

Takes a (claim_text, evidence_content) pair and asks an LLM for a structured
JSON verdict. Used by ClaimVerifier to supplement the lexical-overlap gate.

Contract (strict JSON from the LLM):
    {"verdict": "supported" | "not_supported", "span": "<quoted evidence span>"}
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from harness_core.messages import Message
from harness_core.models import LLMProvider

_SYSTEM = """You are a strict claim verification judge.
Given a CLAIM and one or more EVIDENCE snippets, decide whether the evidence
actually supports the claim. Return ONLY JSON:
{"verdict": "supported" | "not_supported", "span": "<short quoted span from the evidence, or empty>"}
No other text."""


@dataclass
class JudgeVerdict:
    supported: bool
    span: str
    raw: str


class LLMJudge:
    """Thin wrapper around LLMProvider.generate() for claim verification."""

    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    def judge(self, claim_text: str, evidence_content: list[str]) -> JudgeVerdict:
        evidence_block = "\n---\n".join(
            f"[evidence {i + 1}] {c}" for i, c in enumerate(evidence_content)
        )
        reply = self.llm.generate(
            messages=[
                Message.system(_SYSTEM),
                Message.user(
                    f"CLAIM:\n{claim_text}\n\nEVIDENCE:\n{evidence_block}\n\n"
                    "Emit the JSON verdict now."
                ),
            ],
            max_tokens=300,
            temperature=0.0,
        )
        raw = (reply.content or "").strip()
        try:
            data = json.loads(raw)
            supported = str(data.get("verdict", "")).lower() == "supported"
            span = str(data.get("span", ""))
            return JudgeVerdict(supported=supported, span=span, raw=raw)
        except (json.JSONDecodeError, TypeError):
            lowered = raw.lower()
            supported = "supported" in lowered and "not_supported" not in lowered
            return JudgeVerdict(supported=supported, span="", raw=raw)
