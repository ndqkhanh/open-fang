"""PDF fetcher with on-disk caching. Skeleton — ships in Phase 2."""
from __future__ import annotations

from pathlib import Path


class PDFFetcher:
    def __init__(self, *, cache_dir: Path = Path(".cache/pdfs")) -> None:
        self.cache_dir = cache_dir

    def fetch(self, arxiv_id: str) -> bytes:
        raise NotImplementedError("PDFFetcher ships in Phase 2")
