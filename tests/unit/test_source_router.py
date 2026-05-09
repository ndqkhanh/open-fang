from __future__ import annotations

from open_fang.models import Evidence, SourceRef
from open_fang.sources.mock import MockSource
from open_fang.sources.router import SourceRouter, from_single


def _ev(kind: str, ident: str) -> Evidence:
    return Evidence(
        source=SourceRef(kind=kind, identifier=ident, title=ident),
        content=f"content for {ident}",
    )


def test_router_dispatches_by_kind():
    arxiv = MockSource(canned=[_ev("arxiv", "a1")])
    s2 = MockSource(canned=[_ev("s2", "s1")])
    github = MockSource(canned=[_ev("github", "g1")])
    router = SourceRouter(arxiv=arxiv, s2=s2, github=github)

    assert router.search("search.arxiv", "q")[0].source.identifier == "a1"
    assert router.search("search.semantic_scholar", "q")[0].source.identifier == "s1"
    assert router.search("search.github", "q")[0].source.identifier == "g1"


def test_router_uses_fallback_when_kind_missing():
    fb = MockSource(canned=[_ev("arxiv", "fb")])
    router = SourceRouter(fallback=fb)
    assert router.search("search.arxiv", "q")[0].source.identifier == "fb"
    assert router.search("search.github", "q")[0].source.identifier == "fb"


def test_router_returns_empty_when_no_source():
    router = SourceRouter()
    assert router.search("search.arxiv", "q") == []


def test_from_single_wraps_one_source():
    one = MockSource(canned=[_ev("arxiv", "x")])
    router = from_single(one)
    assert router.search("search.arxiv", "q")[0].source.identifier == "x"
    assert router.search("search.github", "q")[0].source.identifier == "x"
