"""External source adapters: arxiv, Semantic Scholar, GitHub, mock."""
from .arxiv import ArxivSource
from .github import GithubSource
from .mock import MockSource
from .router import SearchSource, SourceRouter, from_single
from .semantic_scholar import S2Source

__all__ = [
    "ArxivSource",
    "GithubSource",
    "MockSource",
    "S2Source",
    "SearchSource",
    "SourceRouter",
    "from_single",
]
