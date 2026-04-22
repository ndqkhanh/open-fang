"""PermissionBridge: runtime-enforced risk tiers; not prompt-wrapped."""
from __future__ import annotations

from typing import Literal

from .tokens import TokenRegistry

Verdict = Literal["allow", "park", "deny"]


class PermissionBridge:
    """Compare a proposed op's risk against the user's standing authorization."""

    def __init__(self, *, tokens: TokenRegistry | None = None) -> None:
        self.tokens = tokens or TokenRegistry()

    def check(self, op: str, *, risk: Literal["low", "medium", "high"]) -> Verdict:
        if risk == "low":
            return "allow"
        if self.tokens.has_token(op):
            return "allow"
        if risk == "high":
            return "deny"
        return "park"
