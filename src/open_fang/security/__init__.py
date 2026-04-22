"""Agent-security probes + red-team subagent (v2.5).

Probes inject adversarial content into evidence to exercise the verifier's
rejection paths. The red-team subagent inspects finished reports and tries
to construct a minimally-modified evidence set that would flip verification
without being flagged.
"""
from .probes import (
    AdversarialKBProbe,
    CitationPoisoningProbe,
    InstructionHidingProbe,
    PromptInjectionProbe,
    SecurityProbe,
)

__all__ = [
    "AdversarialKBProbe",
    "CitationPoisoningProbe",
    "InstructionHidingProbe",
    "PromptInjectionProbe",
    "SecurityProbe",
]
