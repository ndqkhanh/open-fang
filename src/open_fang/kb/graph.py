"""Citation-graph edge kinds + subgraph construction for the viewer endpoint.

`build_subgraph` returns a cytoscape-friendly `{nodes, edges}` payload, BFS
out from a seed (or FTS5-matched query) up to `depth` hops. Used by the
`GET /v1/kb/graph` endpoint and by ad-hoc debugging scripts.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Literal

from .store import KBStore

EDGE_KINDS: tuple[str, ...] = (
    "cites",
    "extends",
    "refutes",
    "shares-author",
    "same-benchmark",
    "same-technique-family",
)

Direction = Literal["out", "in", "both"]


@dataclass
class GraphNode:
    id: str
    title: str
    kind: str  # arxiv | s2 | github | kb | ...
    authors: list[str] = field(default_factory=list)
    published_at: str | None = None


@dataclass
class GraphEdge:
    source: str
    target: str
    kind: str  # one of EDGE_KINDS


@dataclass
class Subgraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    seed_id: str | None
    depth: int

    def to_dict(self) -> dict:
        """Cytoscape-friendly JSON shape. Nested under `data` for each element."""
        return {
            "seed_id": self.seed_id,
            "depth": self.depth,
            "nodes": [
                {
                    "data": {
                        "id": n.id,
                        "label": n.title or n.id,
                        "kind": n.kind,
                        "authors": n.authors,
                        "published_at": n.published_at,
                    }
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "data": {
                        "id": f"{e.source}->{e.target}:{e.kind}",
                        "source": e.source,
                        "target": e.target,
                        "kind": e.kind,
                    }
                }
                for e in self.edges
            ],
        }


def build_subgraph(
    kb: KBStore,
    *,
    seed_id: str | None = None,
    query: str | None = None,
    depth: int = 2,
    direction: Direction = "both",
    max_nodes: int = 200,
) -> Subgraph:
    """Build a BFS subgraph around a seed paper.

    When `seed_id` is None, resolves from `query` via FTS5 top-1; if neither
    is provided, returns an empty subgraph. `depth` is the maximum hop count;
    `direction` controls edge traversal (`out` / `in` / `both`).
    """
    seed = _resolve_seed(kb, seed_id=seed_id, query=query)
    if seed is None:
        return Subgraph(nodes=[], edges=[], seed_id=None, depth=depth)

    # BFS on `direction`-traversal edges up to `depth` hops.
    visited_nodes: dict[str, GraphNode] = {}
    visited_edges: set[tuple[str, str, str]] = set()
    edges_out: list[GraphEdge] = []

    seed_node = _node_from_kb(kb, seed)
    if seed_node is None:
        return Subgraph(nodes=[], edges=[], seed_id=seed, depth=depth)
    visited_nodes[seed] = seed_node

    queue: deque[tuple[str, int]] = deque([(seed, 0)])
    while queue and len(visited_nodes) < max_nodes:
        current, hop = queue.popleft()
        if hop >= depth:
            continue
        neighbors = _neighbors(kb, current, direction)
        for src, dst, kind in neighbors:
            edge_key = (src, dst, kind)
            if edge_key not in visited_edges:
                visited_edges.add(edge_key)
                edges_out.append(GraphEdge(source=src, target=dst, kind=kind))
            other = dst if src == current else src
            if other in visited_nodes:
                continue
            node = _node_from_kb(kb, other)
            if node is None:
                continue
            visited_nodes[other] = node
            queue.append((other, hop + 1))
            if len(visited_nodes) >= max_nodes:
                break

    return Subgraph(
        nodes=list(visited_nodes.values()),
        edges=edges_out,
        seed_id=seed,
        depth=depth,
    )


def _resolve_seed(kb: KBStore, *, seed_id: str | None, query: str | None) -> str | None:
    if seed_id is not None:
        return seed_id if kb.get_paper(seed_id) is not None else None
    if query:
        hits = kb.search(query, limit=1)
        if hits:
            return hits[0].source.identifier
    return None


def _node_from_kb(kb: KBStore, paper_id: str) -> GraphNode | None:
    ev = kb.get_paper(paper_id)
    if ev is None:
        return None
    return GraphNode(
        id=paper_id,
        title=ev.source.title,
        kind=ev.source.kind,
        authors=list(ev.source.authors),
        published_at=ev.source.published_at,
    )


def _neighbors(kb: KBStore, paper_id: str, direction: Direction) -> list[tuple[str, str, str]]:
    """Return (src, dst, kind) tuples for edges incident to `paper_id`."""
    edges = kb.list_edges(paper_id)
    out: list[tuple[str, str, str]] = []
    for src, dst, kind in edges:
        if direction == "out" and src != paper_id:
            continue
        if direction == "in" and dst != paper_id:
            continue
        out.append((src, dst, kind))
    return out
