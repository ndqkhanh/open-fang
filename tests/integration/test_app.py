from __future__ import annotations

from fastapi.testclient import TestClient

from open_fang.app import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "open-fang"}


def test_research_endpoint_returns_report():
    r = client.post(
        "/v1/research",
        json={"question": "what is rewoo", "max_cost_usd": 0.1, "target_length_words": 500},
    )
    assert r.status_code == 200
    body = r.json()
    assert "sections" in body
    assert "faithfulness_ratio" in body
    assert "dag_id" in body
