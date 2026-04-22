"""FastAPI HTTP surface for OpenFang."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from harness_core.models import AnthropicLLM, get_default_llm
from pydantic import BaseModel, Field

from .kb.graph import build_subgraph
from .kb.store import KBStore
from .memory.store import MemoryStore
from .models import Brief, Report
from .permissions.bridge import PermissionBridge
from .permissions.tokens import TokenRegistry
from .pipeline import OpenFangPipeline
from .planner.llm_planner import DAGPlanner
from .scheduler.engine import SchedulerEngine
from .sources.arxiv import ArxivSource
from .sources.mock import MockSource
from .supervisor.registry import Supervisor, default_supervisor
from .verify.claim_verifier import ClaimVerifier

app = FastAPI(
    title="OpenFang",
    description="Autonomous AI research agent for AI / Agentic AI / Harness Engineering literature.",
    version="0.1.0",
)

# Module-level state persists across requests. For multi-tenant deployments
# swap these for per-user stores.
_tokens = TokenRegistry()
_bridge = PermissionBridge(tokens=_tokens)
_kb: KBStore | None = None
_supervisor: Supervisor = default_supervisor()


def _build_default_pipeline() -> tuple[OpenFangPipeline, dict[str, object]]:
    """Build the default HTTP pipeline.

    Live mode (real arxiv source + AnthropicLLM-backed planner/verifier) is
    activated when ``ANTHROPIC_API_KEY`` is set and the ``anthropic`` package
    is importable. Otherwise falls back to MockSource + MockLLM so that
    container/test environments still boot.
    """
    llm = get_default_llm()
    live = isinstance(llm, AnthropicLLM)
    if live:
        source = ArxivSource(email=os.environ.get("ARXIV_EMAIL", "").strip())
    else:
        source = MockSource()
    pipeline = OpenFangPipeline(
        planner=DAGPlanner(llm=llm if live else None),
        scheduler=SchedulerEngine(
            source=source,
            permission_bridge=_bridge,
            supervisor=_supervisor,
        ),
        verifier=ClaimVerifier(llm=llm if live else None),
    )
    info = {
        "mode": "live" if live else "mock",
        "llm": type(llm).__name__,
        "source": type(source).__name__,
    }
    return pipeline, info


_pipeline, _runtime_info = _build_default_pipeline()


def _get_kb() -> KBStore | None:
    """Lazy-open the KB when a `/v1/kb/*` request arrives."""
    global _kb
    if _kb is not None:
        return _kb
    path = os.environ.get("OPEN_FANG_DB_PATH", "").strip()
    if not path:
        return None
    _kb = KBStore(db_path=Path(path)).open()
    return _kb


def _set_kb_for_testing(kb: KBStore | None) -> None:
    """Let test fixtures swap in an in-memory KB without touching env vars."""
    global _kb
    _kb = kb


class ApproveRequest(BaseModel):
    op: str = Field(..., description="Node kind to authorize, e.g. 'fetch.pdf'.")
    kind: Literal["session", "once", "pattern"] = "session"


class ApproveResponse(BaseModel):
    granted: str
    kind: str


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "open-fang"}


@app.get("/v1/info")
def runtime_info() -> dict[str, object]:
    """Report active pipeline mode and components — useful for debugging
    whether the server is in live (real arxiv + LLM) or mock mode."""
    return _runtime_info


@app.post("/v1/research", response_model=Report)
def create_research(brief: Brief) -> Report:
    result = _pipeline.run(brief)
    return result.report


@app.post("/v1/permissions/approve", response_model=ApproveResponse)
def approve_permission(req: ApproveRequest) -> ApproveResponse:
    _tokens.grant(req.op, kind=req.kind)
    return ApproveResponse(granted=req.op, kind=req.kind)


# -------------------------------------------------------------------------
# Memory endpoints (v3.1 — progressive disclosure). Active only when a KB is
# configured, since observations share the KB's SQLite connection.
# -------------------------------------------------------------------------


@app.get("/v1/memory/timeline")
def memory_timeline(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
) -> dict:
    kb = _get_kb()
    if kb is None:
        raise HTTPException(status_code=404, detail="KB not configured")
    memory = MemoryStore(kb)
    observations = memory.timeline(offset=offset, limit=limit)
    return {
        "offset": offset,
        "limit": limit,
        "total": memory.count(),
        "observations": [
            {
                "id": o.id,
                "trace_id": o.trace_id,
                "node_id": o.node_id,
                "node_kind": o.node_kind,
                "stage": o.stage,
                "verdict": o.verdict,
                "timestamp": o.timestamp,
                "compact_summary": o.compact_summary,
                "detail_summary": o.detail_summary,
            }
            for o in observations
        ],
    }


@app.get("/v1/supervisor/status")
def supervisor_status() -> dict:
    """Return the specialist roster + per-specialist dispatch stats."""
    return {
        "roster": _supervisor.roster(),
        "stats": {
            name: {"dispatched": stat.dispatched, "errors": stat.errors}
            for name, stat in _supervisor.stats.per_specialist.items()
        },
    }


@app.get("/v1/memory/observation/{observation_id}")
def memory_observation(observation_id: str) -> dict:
    kb = _get_kb()
    if kb is None:
        raise HTTPException(status_code=404, detail="KB not configured")
    observation = MemoryStore(kb).get_observation(observation_id)
    if observation is None:
        raise HTTPException(
            status_code=404, detail=f"observation {observation_id!r} not found"
        )
    return {
        "id": observation.id,
        "trace_id": observation.trace_id,
        "node_id": observation.node_id,
        "node_kind": observation.node_kind,
        "stage": observation.stage,
        "verdict": observation.verdict,
        "timestamp": observation.timestamp,
        "compact_summary": observation.compact_summary,
        "detail_summary": observation.detail_summary,
        "full_json": observation.full_json,
    }


# -------------------------------------------------------------------------
# KB endpoints — active only when a KB is configured via OPEN_FANG_DB_PATH
# or via `_set_kb_for_testing`.
# -------------------------------------------------------------------------


@app.get("/v1/kb/papers")
def list_papers() -> dict:
    kb = _get_kb()
    if kb is None:
        raise HTTPException(status_code=404, detail="KB not configured")
    papers = kb.sample_papers(limit=200)
    return {
        "papers": [
            {
                "id": e.source.identifier,
                "title": e.source.title,
                "kind": e.source.kind,
                "authors": e.source.authors,
                "published_at": e.source.published_at,
            }
            for e in papers
        ]
    }


@app.get("/v1/kb/paper/{paper_id:path}")
def get_paper(paper_id: str) -> dict:
    kb = _get_kb()
    if kb is None:
        raise HTTPException(status_code=404, detail="KB not configured")
    ev = kb.get_paper(paper_id)
    if ev is None:
        raise HTTPException(status_code=404, detail=f"paper {paper_id!r} not found")
    return {
        "id": ev.source.identifier,
        "title": ev.source.title,
        "kind": ev.source.kind,
        "authors": ev.source.authors,
        "published_at": ev.source.published_at,
        "abstract": ev.content,
        "edges": [
            {"src": src, "dst": dst, "kind": kind}
            for src, dst, kind in kb.list_edges(paper_id)
        ],
    }


@app.get("/v1/kb/graph")
def kb_graph(
    seed: str | None = Query(default=None, description="Seed paper id (e.g. arxiv:2305.18323)"),
    query: str | None = Query(default=None, description="FTS5 query to resolve a seed paper"),
    depth: int = Query(default=2, ge=1, le=5),
    direction: Literal["out", "in", "both"] = Query(default="both"),
    max_nodes: int = Query(default=100, ge=1, le=500),
) -> dict:
    kb = _get_kb()
    if kb is None:
        raise HTTPException(status_code=404, detail="KB not configured")
    if not seed and not query:
        raise HTTPException(status_code=400, detail="provide either ?seed=... or ?query=...")
    subgraph = build_subgraph(
        kb,
        seed_id=seed,
        query=query,
        depth=depth,
        direction=direction,
        max_nodes=max_nodes,
    )
    return subgraph.to_dict()


# -------------------------------------------------------------------------
# Static viewer — mounted at /viewer when web/graph exists.
# -------------------------------------------------------------------------

_VIEWER_DIR = Path(__file__).resolve().parents[2] / "web" / "graph"
if _VIEWER_DIR.exists():
    app.mount("/viewer", StaticFiles(directory=_VIEWER_DIR, html=True), name="viewer")

    @app.get("/")
    def root_redirect_to_viewer() -> FileResponse:
        return FileResponse(_VIEWER_DIR / "index.html")
