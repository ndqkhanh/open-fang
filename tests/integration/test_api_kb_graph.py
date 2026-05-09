"""v2.3 contract tests for /v1/kb/papers, /v1/kb/paper/{id}, /v1/kb/graph."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from open_fang import app as app_module
from open_fang.kb.store import KBStore
from open_fang.models import SourceRef

client = TestClient(app_module.app)


@pytest.fixture
def kb_in_app():
    """Swap in an in-memory KB for the duration of the test and tear down."""
    kb = KBStore(db_path=":memory:").open()
    for aid, title in [
        ("arxiv:rewoo", "ReWOO"),
        ("arxiv:react", "ReAct"),
        ("arxiv:voyager", "Voyager"),
    ]:
        kb.upsert_paper(
            SourceRef(kind="arxiv", identifier=aid, title=title, authors=["X"]),
            abstract=f"{title} abstract.",
        )
    kb.add_edge("arxiv:rewoo", "arxiv:react", "extends")
    kb.add_edge("arxiv:voyager", "arxiv:react", "cites")
    app_module._set_kb_for_testing(kb)
    yield kb
    app_module._set_kb_for_testing(None)


def test_kb_endpoints_404_when_kb_not_configured():
    # Ensure no KB is wired (fixture above is not applied to this test).
    app_module._set_kb_for_testing(None)
    assert client.get("/v1/kb/papers").status_code == 404
    assert client.get("/v1/kb/paper/anything").status_code == 404
    assert client.get("/v1/kb/graph?seed=arxiv:x").status_code == 404


def test_list_papers_returns_seeded_entries(kb_in_app):
    r = client.get("/v1/kb/papers")
    assert r.status_code == 200
    body = r.json()
    ids = sorted(p["id"] for p in body["papers"])
    assert ids == ["arxiv:react", "arxiv:rewoo", "arxiv:voyager"]


def test_get_paper_returns_full_record(kb_in_app):
    r = client.get("/v1/kb/paper/arxiv:rewoo")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "arxiv:rewoo"
    assert body["title"] == "ReWOO"
    assert "abstract" in body
    kinds = sorted(e["kind"] for e in body["edges"])
    assert kinds == ["extends"]


def test_get_paper_404_on_missing(kb_in_app):
    assert client.get("/v1/kb/paper/arxiv:nope").status_code == 404


def test_graph_requires_seed_or_query(kb_in_app):
    r = client.get("/v1/kb/graph")
    assert r.status_code == 400


def test_graph_returns_cytoscape_shape(kb_in_app):
    r = client.get("/v1/kb/graph?seed=arxiv:rewoo&depth=1")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"seed_id", "depth", "nodes", "edges"}
    assert body["seed_id"] == "arxiv:rewoo"
    for node in body["nodes"]:
        assert "data" in node and "id" in node["data"]
    for edge in body["edges"]:
        assert "data" in edge
        for k in ("source", "target", "kind"):
            assert k in edge["data"]


def test_graph_query_resolves_via_fts(kb_in_app):
    r = client.get("/v1/kb/graph?query=voyager&depth=1")
    assert r.status_code == 200
    body = r.json()
    assert body["seed_id"] == "arxiv:voyager"
    ids = sorted(n["data"]["id"] for n in body["nodes"])
    assert "arxiv:voyager" in ids


def test_graph_depth_clamped_to_range(kb_in_app):
    # depth must be in [1,5]; out-of-range returns 422 from pydantic validation
    assert client.get("/v1/kb/graph?seed=arxiv:rewoo&depth=0").status_code == 422
    assert client.get("/v1/kb/graph?seed=arxiv:rewoo&depth=99").status_code == 422


def test_viewer_static_mount_serves_index():
    """The /viewer route serves the static HTML when web/graph/ exists."""
    r = client.get("/viewer/")
    # Either the viewer is mounted (200) or the project was built without the
    # web/graph/ assets (404). Both are acceptable; just verify no 500s.
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert "OpenFang" in r.text
