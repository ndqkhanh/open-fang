from __future__ import annotations

import json

from harness_core.models import MockLLM

from open_fang.models import Brief
from open_fang.planner.llm_planner import DAGPlanner


def _brief() -> Brief:
    return Brief(question="what is rewoo")


def test_llm_planner_parses_valid_json():
    dag_json = {
        "nodes": [
            {"id": "A", "kind": "search.arxiv", "args": {"query": "x"}, "depends_on": [], "risk": "low"},
            {"id": "B", "kind": "synthesize.briefing", "args": {}, "depends_on": ["A"], "risk": "low"},
        ],
        "estimated_cost_usd": 0.17,
    }
    llm = MockLLM(scripted_outputs=[json.dumps(dag_json)])
    dag = DAGPlanner(llm=llm).plan(_brief())
    assert [n.id for n in dag.nodes] == ["A", "B"]
    assert dag.estimated_cost_usd == 0.17


def test_llm_planner_falls_back_on_invalid_json():
    llm = MockLLM(scripted_outputs=["this is not json"])
    dag = DAGPlanner(llm=llm).plan(_brief())
    # Fallback is the 6-node canonical DAG
    assert len(dag.nodes) == 6
    assert dag.nodes[0].id == "R1"


def test_llm_planner_falls_back_on_unknown_kind():
    dag_json = {
        "nodes": [
            {"id": "A", "kind": "not.a.real.kind", "args": {}, "depends_on": [], "risk": "low"}
        ]
    }
    llm = MockLLM(scripted_outputs=[json.dumps(dag_json)])
    dag = DAGPlanner(llm=llm).plan(_brief())
    assert len(dag.nodes) == 6  # canonical fallback


def test_llm_planner_falls_back_on_empty_reply():
    llm = MockLLM(scripted_outputs=[""])
    dag = DAGPlanner(llm=llm).plan(_brief())
    assert len(dag.nodes) == 6


def test_llm_planner_rejects_dag_with_missing_dep():
    dag_json = {
        "nodes": [
            {"id": "A", "kind": "search.arxiv", "args": {}, "depends_on": ["Z"], "risk": "low"}
        ]
    }
    llm = MockLLM(scripted_outputs=[json.dumps(dag_json)])
    dag = DAGPlanner(llm=llm).plan(_brief())
    # Invalid DAG → fallback, not crash
    assert len(dag.nodes) == 6


def test_no_llm_is_deterministic_canonical():
    dag = DAGPlanner().plan(_brief())
    assert [n.id for n in dag.nodes] == ["R1", "R2", "R3", "R4", "R5", "R6"]
