"""Supervisor + 5 specialist subagents (v3.2).

Each specialist owns a set of DAG node kinds and exposes a uniform
`execute(node, context)` method. The Supervisor routes a scheduler dispatch
through the first specialist that claims the kind; unclaimed kinds fall
through to the scheduler's default behavior.

v3.2 MVP uses synchronous in-process dispatch with try/except isolation.
v4 introduces the opt-in Conductor-style isolated-session mode.
"""
from .isolated import IsolatedSupervisor, IsolatedSupervisorConfig, isolated_mode_enabled
from .registry import Supervisor, SupervisorStats, default_supervisor
from .specialist import (
    ClaimVerifierAgent,
    CriticAgent,
    DeepReadAgent,
    Specialist,
    SpecialistContext,
    SpecialistOutcome,
    SurveyAgent,
    SynthesisAgent,
)

__all__ = [
    "ClaimVerifierAgent",
    "CriticAgent",
    "DeepReadAgent",
    "IsolatedSupervisor",
    "IsolatedSupervisorConfig",
    "Specialist",
    "SpecialistContext",
    "SpecialistOutcome",
    "Supervisor",
    "SupervisorStats",
    "SurveyAgent",
    "SynthesisAgent",
    "default_supervisor",
    "isolated_mode_enabled",
]
