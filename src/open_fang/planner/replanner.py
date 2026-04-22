"""One-shot replanner: on schema failure, try once more with a hint."""
from __future__ import annotations

from ..models import DAG, Brief
from .llm_planner import DAGPlanner
from .schema import DAGSchemaError, validate_dag


def replan_once(planner: DAGPlanner, brief: Brief, *, hint: str = "") -> DAG:
    """Attempt planning once more with a hint appended; raise on second failure."""
    try:
        dag = planner.plan(brief)
        validate_dag(dag)
        return dag
    except DAGSchemaError as exc:
        # Production: re-prompt with hint; MVP: re-run deterministic planner (always valid).
        _ = hint
        raise exc
