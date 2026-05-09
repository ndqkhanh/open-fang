"""12 canonical primitives for failure attribution (v6.0).

Versioned vocabulary — changing the enum is a breaking change per v6-plan.md §CC-2.
"""
from __future__ import annotations

from enum import Enum


class Primitive(str, Enum):
    PLANNER = "planner"
    SCHEDULER_DISPATCH = "scheduler-dispatch"
    SOURCE_ROUTER = "source-router"
    KB_LOOKUP = "kb-lookup"
    SYNTHESIS = "synthesis"
    MUTATION_PROBE = "mutation-probe"
    LLM_JUDGE = "llm-judge"
    EXECUTABLE_VERIFIER = "executable-verifier"
    CRITIC = "critic"
    MEMORY_COMPACT = "memory-compact"
    SKILL_ACTIVATION = "skill-activation"
    PERMISSION_GATE = "permission-gate"


PRIMITIVES: tuple[Primitive, ...] = tuple(Primitive)
