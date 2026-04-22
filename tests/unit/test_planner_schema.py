from __future__ import annotations

import pytest

from open_fang.models import DAG, Brief, Node
from open_fang.planner.llm_planner import DAGPlanner
from open_fang.planner.schema import DAGSchemaError, validate_dag


def test_planner_produces_valid_dag():
    planner = DAGPlanner()
    dag = planner.plan(Brief(question="what is rewoo"))
    assert len(dag.nodes) >= 3
    validate_dag(dag)


def test_planner_rejects_empty_question():
    with pytest.raises(ValueError):
        DAGPlanner().plan(Brief(question="   "))


def test_validate_dag_detects_cycle():
    dag = DAG(
        nodes=[
            Node(id="A", kind="reason", depends_on=["B"]),
            Node(id="B", kind="reason", depends_on=["A"]),
        ]
    )
    with pytest.raises(DAGSchemaError):
        validate_dag(dag)


def test_validate_dag_detects_missing_dep():
    dag = DAG(nodes=[Node(id="A", kind="reason", depends_on=["Z"])])
    with pytest.raises(DAGSchemaError):
        validate_dag(dag)


def test_validate_dag_detects_duplicate_id():
    dag = DAG(
        nodes=[
            Node(id="A", kind="reason"),
            Node(id="A", kind="reason"),
        ]
    )
    with pytest.raises(DAGSchemaError):
        validate_dag(dag)
