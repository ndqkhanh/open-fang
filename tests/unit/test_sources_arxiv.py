from __future__ import annotations

import httpx

from open_fang.sources.arxiv import ArxivSource

_ATOM_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2305.18323v1</id>
    <title>ReWOO: Decoupling Reasoning from Observations</title>
    <summary>ReWOO decouples reasoning from observations using a planner that
emits a DAG of tool calls resolved in parallel.</summary>
    <published>2023-05-23T14:00:00Z</published>
    <author><name>Binfeng Xu</name></author>
    <author><name>Zhiyuan Peng</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2210.03629v3</id>
    <title>ReAct: Synergizing Reasoning and Acting</title>
    <summary>ReAct interleaves reasoning and acting in a single loop.</summary>
    <published>2022-10-06T00:00:00Z</published>
    <author><name>Shunyu Yao</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/without.summary</id>
    <title>Empty summary paper</title>
    <summary></summary>
  </entry>
</feed>
"""


def _client_returning(payload: bytes, capture: dict) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        capture["url"] = str(request.url)
        return httpx.Response(200, content=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_arxiv_source_parses_atom_entries():
    capture: dict = {}
    client = _client_returning(_ATOM_SAMPLE, capture)
    source = ArxivSource(client=client)
    evidence = source.search("rewoo", max_results=5)

    assert len(evidence) == 2  # third entry skipped (empty summary)
    first, second = evidence
    assert first.source.identifier == "arxiv:2305.18323"  # version stripped
    assert first.source.title.startswith("ReWOO")
    assert first.source.authors == ["Binfeng Xu", "Zhiyuan Peng"]
    assert "decouples" in first.content
    assert first.channel == "abstract"

    assert second.source.identifier == "arxiv:2210.03629"


def test_arxiv_source_passes_query_params():
    capture: dict = {}
    client = _client_returning(_ATOM_SAMPLE, capture)
    ArxivSource(client=client).search("agentic rag", max_results=3)
    assert "search_query=all%3Aagentic+rag" in capture["url"] or "all:agentic rag" in capture["url"]
    assert "max_results=3" in capture["url"]


def test_arxiv_source_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    import pytest

    with pytest.raises(httpx.HTTPStatusError):
        ArxivSource(client=client).search("x")
