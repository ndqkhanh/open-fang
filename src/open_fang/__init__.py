"""OpenFang: autonomous AI research agent for AI / Agentic AI / Harness Engineering literature.

Two-phase SemaClaw-shaped loop:
    Phase 1 — LLM planner emits a typed research DAG from Brief + FANG.md + KB.
    Phase 2 — deterministic scheduler walks the DAG, parallelizes independent
    branches, parks permission-gated nodes, retries at node granularity.

Public API:
    - OpenFangPipeline: orchestrates brief → DAG → execution → report
    - Brief, DAG, Node, Claim, Evidence, Report: data model
"""
from __future__ import annotations

from .models import (
    DAG,
    Brief,
    Claim,
    Evidence,
    Node,
    Report,
    Section,
    SourceRef,
    Span,
)
from .pipeline import OpenFangPipeline, PipelineResult

__all__ = [
    "DAG",
    "Brief",
    "Claim",
    "Evidence",
    "Node",
    "OpenFangPipeline",
    "PipelineResult",
    "Report",
    "Section",
    "SourceRef",
    "Span",
]
