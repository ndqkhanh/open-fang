from __future__ import annotations

from fastapi.testclient import TestClient

from open_fang.app import app

client = TestClient(app)


def test_supervisor_status_returns_roster():
    r = client.get("/v1/supervisor/status")
    assert r.status_code == 200
    body = r.json()
    roster_names = sorted(entry["name"] for entry in body["roster"])
    # v4.0 expanded to 9 specialists.
    assert roster_names == [
        "claim-verifier", "critic", "deep-read", "methodologist",
        "publisher", "research-director", "survey", "synthesis",
        "threat-modeler",
    ]
    for entry in body["roster"]:
        assert "stage" in entry
        assert "handles" in entry and isinstance(entry["handles"], list)


def test_supervisor_status_stats_are_populated_after_research_call():
    # Reset by triggering at least one research run through the default pipeline.
    client.post("/v1/research", json={"question": "rewoo vs react", "target_length_words": 300})
    body = client.get("/v1/supervisor/status").json()
    # After a /v1/research round, the survey specialist has ≥1 dispatch.
    assert "survey" in body["stats"]
    assert body["stats"]["survey"]["dispatched"] >= 1
