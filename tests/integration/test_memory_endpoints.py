from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from open_fang import app as app_module
from open_fang.kb.store import KBStore
from open_fang.memory.store import MemoryStore
from open_fang.models import Span

client = TestClient(app_module.app)


@pytest.fixture
def kb_with_observations():
    kb = KBStore(db_path=":memory:").open()
    memory = MemoryStore(kb)
    for i in range(5):
        memory.append(
            Span(
                trace_id=f"t{i}",
                node_id=f"n{i}",
                kind="search.arxiv",  # type: ignore[arg-type]
                started_at=float(i),
                ended_at=float(i) + 0.2,
                verdict="ok",  # type: ignore[arg-type]
            )
        )
    app_module._set_kb_for_testing(kb)
    yield kb
    app_module._set_kb_for_testing(None)


def test_timeline_endpoint_returns_paginated_observations(kb_with_observations):
    r = client.get("/v1/memory/timeline?limit=3")
    assert r.status_code == 200
    body = r.json()
    assert body["limit"] == 3
    assert body["total"] == 5
    assert len(body["observations"]) == 3
    first = body["observations"][0]
    for k in ("id", "trace_id", "node_id", "compact_summary", "timestamp"):
        assert k in first


def test_observation_endpoint_returns_full_json(kb_with_observations):
    listing = client.get("/v1/memory/timeline?limit=1").json()
    obs_id = listing["observations"][0]["id"]
    r = client.get(f"/v1/memory/observation/{obs_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == obs_id
    assert "full_json" in body
    assert body["full_json"]["kind"] == "search.arxiv"


def test_observation_404_on_missing_id(kb_with_observations):
    r = client.get("/v1/memory/observation/does-not-exist")
    assert r.status_code == 404


def test_memory_endpoints_404_when_kb_not_configured():
    app_module._set_kb_for_testing(None)
    assert client.get("/v1/memory/timeline").status_code == 404
    assert client.get("/v1/memory/observation/anything").status_code == 404


def test_timeline_offset_skips_entries(kb_with_observations):
    r = client.get("/v1/memory/timeline?offset=3&limit=10")
    assert r.status_code == 200
    body = r.json()
    assert len(body["observations"]) == 2  # only 2 left after offset=3 of 5
