"""End-to-end Phase-5 check: POST /v1/permissions/approve grants a token,
then the next /v1/research run lets a medium-risk node proceed.

The default pipeline in app.py uses the same module-level PermissionBridge as
the approval endpoint, so approvals persist across requests within the process.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from open_fang.app import _bridge, _tokens, app

client = TestClient(app)


def _reset_tokens() -> None:
    _tokens.tokens.clear()


def test_approve_endpoint_grants_session_token():
    _reset_tokens()
    r = client.post("/v1/permissions/approve", json={"op": "fetch.pdf", "kind": "session"})
    assert r.status_code == 200
    body = r.json()
    assert body == {"granted": "fetch.pdf", "kind": "session"}

    # Bridge must now allow the medium-risk op.
    assert _bridge.check(op="fetch.pdf", risk="medium") == "allow"


def test_approve_once_token_consumed_after_first_check():
    _reset_tokens()
    client.post("/v1/permissions/approve", json={"op": "fetch.paywalled", "kind": "once"})
    assert _bridge.check(op="fetch.paywalled", risk="medium") == "allow"
    # Consumed; the next medium-risk check parks again.
    assert _bridge.check(op="fetch.paywalled", risk="medium") == "park"


def test_research_endpoint_still_works_with_permissions_wired():
    _reset_tokens()
    r = client.post(
        "/v1/research",
        json={"question": "rewoo vs react", "max_cost_usd": 0.1, "target_length_words": 300},
    )
    assert r.status_code == 200
    assert "faithfulness_ratio" in r.json()
