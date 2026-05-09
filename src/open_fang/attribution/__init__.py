"""Primitive-level failure attribution (v6.0, HAFC-lite).

Closes the loop v2.1 EvolvingArena / v2.2 synthesis / v4.3 isolated supervisor
silently assumed. Every pipeline failure resolves to one of 12 canonical
primitives. Rules-based first; optional LLM fallback for ambiguous cases.
"""
from .classifier import AttributionReport, AttributionResult, HAFCClassifier
from .primitives import PRIMITIVES, Primitive

__all__ = [
    "AttributionReport",
    "AttributionResult",
    "HAFCClassifier",
    "PRIMITIVES",
    "Primitive",
]
