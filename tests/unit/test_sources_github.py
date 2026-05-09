from __future__ import annotations

import json

import httpx

from open_fang.sources.github import GithubSource


def _client(payload: dict) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=json.dumps(payload).encode(),
            headers={"content-type": "application/json"},
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_github_source_parses_repo_items():
    payload = {
        "items": [
            {
                "full_name": "midea-ai/SemaClaw",
                "html_url": "https://github.com/midea-ai/SemaClaw",
                "description": "General-purpose personal AI agents via harness engineering.",
                "owner": {"login": "midea-ai"},
                "created_at": "2026-04-13T10:00:00Z",
            },
            {
                "full_name": "empty/desc",
                "html_url": "https://github.com/empty/desc",
                "description": "",
                "owner": {"login": "empty"},
                "created_at": "2024-01-01T00:00:00Z",
            },
        ]
    }
    source = GithubSource(client=_client(payload))
    evidence = source.search("semaclaw")

    assert len(evidence) == 1  # empty-description repo skipped
    e = evidence[0]
    assert e.source.identifier == "https://github.com/midea-ai/SemaClaw"
    assert e.source.kind == "github"
    assert e.source.authors == ["midea-ai"]
    assert e.source.published_at == "2026-04-13"
    assert "harness" in e.content.lower()
