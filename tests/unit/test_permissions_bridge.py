from __future__ import annotations

from open_fang.permissions.bridge import PermissionBridge
from open_fang.permissions.tokens import TokenRegistry


def test_low_risk_allowed_by_default():
    assert PermissionBridge().check("fetch.arxiv", risk="low") == "allow"


def test_medium_risk_parks_without_token():
    assert PermissionBridge().check("fetch.paywalled", risk="medium") == "park"


def test_high_risk_denied_without_token():
    assert PermissionBridge().check("write.filesystem", risk="high") == "deny"


def test_token_grants_medium_risk():
    tokens = TokenRegistry()
    tokens.grant("fetch.paywalled", kind="session")
    bridge = PermissionBridge(tokens=tokens)
    assert bridge.check("fetch.paywalled", risk="medium") == "allow"


def test_once_token_consumed_after_use():
    tokens = TokenRegistry()
    tokens.grant("fetch.paywalled", kind="once")
    bridge = PermissionBridge(tokens=tokens)
    assert bridge.check("fetch.paywalled", risk="medium") == "allow"
    assert bridge.check("fetch.paywalled", risk="medium") == "park"
