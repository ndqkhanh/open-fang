from __future__ import annotations

import json

import httpx

from open_fang.sources.arxiv_native import ArxivNativeSource, ReferenceEdge
from open_fang.sources.github_native import CodeForPaper, GithubNativeSource
from open_fang.sources.huggingface import HFModelLink, HFSource


def _stub_client(status: int = 200, body: str | bytes = "") -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=body if isinstance(body, bytes) else body.encode())

    return httpx.Client(transport=httpx.MockTransport(handler))


def _json_client(payload) -> httpx.Client:
    return _stub_client(body=json.dumps(payload))


# ============================================================================
# ArxivNativeSource
# ============================================================================


def test_fetch_bibtex_returns_body():
    stub = "@article{xu2023rewoo, title={ReWOO}}"
    src = ArxivNativeSource(client=_stub_client(body=stub))
    assert src.fetch_bibtex("2305.18323") == stub


def test_fetch_bibtex_returns_empty_on_404():
    src = ArxivNativeSource(client=_stub_client(status=404))
    assert src.fetch_bibtex("arxiv:missing") == ""


def test_fetch_references_parses_arxiv_ids_in_bibtex_body():
    body = (
        "@inproceedings{xu2023rewoo, title={ReWOO 2305.18323}, "
        "references={2210.03629, 2303.11366}}"
    )
    src = ArxivNativeSource(client=_stub_client(body=body))
    edges = src.fetch_references("2305.18323")
    dst_ids = sorted(e.dst_arxiv_id for e in edges)
    # Own id excluded; remaining ids sorted.
    assert dst_ids == ["2210.03629", "2303.11366"]
    assert all(e.src_arxiv_id == "2305.18323" for e in edges)


def test_fetch_references_excludes_self_reference():
    body = "@article{xu, ids={2305.18323, 2305.18323v2}}"
    src = ArxivNativeSource(client=_stub_client(body=body))
    edges = src.fetch_references("2305.18323")
    assert edges == []


# ============================================================================
# GithubNativeSource
# ============================================================================


def test_find_code_for_paper_parses_pwc_response():
    payload = {
        "results": [
            {"url": "https://github.com/midea-ai/SemaClaw", "stars": 1234},
            {"url": "https://github.com/example/other"},  # missing stars ok
        ]
    }
    src = GithubNativeSource(client=_json_client(payload))
    out = src.find_code_for_paper("2604.11548")
    assert len(out) == 2
    assert out[0].arxiv_id == "2604.11548"
    assert out[0].repo_url == "https://github.com/midea-ai/SemaClaw"
    assert out[0].stars == 1234
    assert out[1].stars is None


def test_find_code_for_paper_returns_empty_on_404():
    src = GithubNativeSource(client=_stub_client(status=404))
    assert src.find_code_for_paper("2604.xxxxx") == []


def test_fetch_repo_readme_returns_evidence():
    src = GithubNativeSource(
        client=_stub_client(body="# my repo\nbody content"),
    )
    ev = src.fetch_repo_readme("midea-ai/SemaClaw")
    assert ev is not None
    assert ev.source.identifier == "https://github.com/midea-ai/SemaClaw"
    assert "my repo" in ev.content


def test_fetch_repo_readme_returns_none_on_error():
    src = GithubNativeSource(client=_stub_client(status=404))
    assert src.fetch_repo_readme("missing/repo") is None


# ============================================================================
# HFSource
# ============================================================================


def test_find_model_by_paper_parses_hf_response():
    payload = [
        {"modelId": "google/gemma-2b", "downloads": 9999},
        {"id": "meta/llama3-8b"},
    ]
    src = HFSource(client=_json_client(payload))
    links = src.find_model_by_paper("2604.00001")
    assert len(links) == 2
    assert links[0].model_id == "google/gemma-2b"
    assert links[0].downloads == 9999
    assert links[1].model_id == "meta/llama3-8b"
    assert links[1].downloads is None


def test_find_model_returns_empty_on_bad_response():
    src = HFSource(client=_stub_client(status=500))
    assert src.find_model_by_paper("2604.xxx") == []


def test_fetch_model_card_returns_evidence():
    src = HFSource(client=_stub_client(body="# Model card\nDetails."))
    ev = src.fetch_model_card("google/gemma-2b")
    assert ev is not None
    assert ev.source.kind == "huggingface"
    assert ev.source.identifier == "hf:google/gemma-2b"


def test_types_exported():
    """Sanity: the public dataclasses are importable and construct cleanly."""
    assert ReferenceEdge(src_arxiv_id="a", dst_arxiv_id="b")
    assert CodeForPaper(arxiv_id="a", repo_url="u", stars=None)
    assert HFModelLink(arxiv_id="a", model_id="m", downloads=None)
