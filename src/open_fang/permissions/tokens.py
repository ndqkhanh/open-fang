"""Authorization tokens: session / approve-once / pattern-bundled."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TokenKind = Literal["session", "once", "pattern"]


@dataclass
class Token:
    op: str
    kind: TokenKind


@dataclass
class TokenRegistry:
    tokens: list[Token] = field(default_factory=list)

    def grant(self, op: str, *, kind: TokenKind = "once") -> None:
        self.tokens.append(Token(op=op, kind=kind))

    def has_token(self, op: str) -> bool:
        for i, tok in enumerate(self.tokens):
            if tok.op == op or (tok.op.endswith("*") and op.startswith(tok.op[:-1])):
                if tok.kind == "once":
                    self.tokens.pop(i)
                return True
        return False
