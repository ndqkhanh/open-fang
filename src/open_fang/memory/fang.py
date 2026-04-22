"""FANG.md loader: persona partition, size-capped, never compacted."""
from __future__ import annotations

from pathlib import Path

DEFAULT_PATH = Path("FANG.md")
MAX_BYTES = 16_000


class FANGLoader:
    """Load a persona partition from disk with a hard size cap."""

    def __init__(self, *, path: Path = DEFAULT_PATH, max_bytes: int = MAX_BYTES) -> None:
        self.path = path
        self.max_bytes = max_bytes

    def load(self) -> str:
        if not self.path.exists():
            return ""
        data = self.path.read_text(encoding="utf-8")
        if len(data.encode("utf-8")) > self.max_bytes:
            raise ValueError(
                f"{self.path} exceeds max_bytes={self.max_bytes} — trim before loading"
            )
        return data
