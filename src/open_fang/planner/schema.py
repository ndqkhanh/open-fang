"""DAG schema validation: cycle detection + orphan detection."""
from __future__ import annotations

from ..models import DAG


class DAGSchemaError(ValueError):
    """Raised when a DAG fails schema validation."""


def validate_dag(dag: DAG) -> None:
    """Validate node IDs are unique, deps resolve, and no cycles exist."""
    seen_ids: set[str] = set()
    for node in dag.nodes:
        if node.id in seen_ids:
            raise DAGSchemaError(f"duplicate node id: {node.id!r}")
        seen_ids.add(node.id)

    for node in dag.nodes:
        for dep in node.depends_on:
            if dep not in seen_ids:
                raise DAGSchemaError(f"node {node.id!r} depends on missing node {dep!r}")

    # Cycle detection via DFS
    visiting: set[str] = set()
    visited: set[str] = set()
    by_id = {n.id: n for n in dag.nodes}

    def dfs(node_id: str) -> None:
        if node_id in visited:
            return
        if node_id in visiting:
            raise DAGSchemaError(f"cycle detected at node {node_id!r}")
        visiting.add(node_id)
        for dep in by_id[node_id].depends_on:
            dfs(dep)
        visiting.discard(node_id)
        visited.add(node_id)

    for node in dag.nodes:
        dfs(node.id)
