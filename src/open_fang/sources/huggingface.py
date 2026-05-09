"""HFSource (v6.3) — HuggingFace model lineage + card adapter.

Resolves paper→model via HF's model-hub search and fetches model-card bodies
as evidence. Model lineage links become `has_model` edges in the KB graph.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..models import Evidence, SourceRef

HF_API = "https://huggingface.co/api"


@dataclass
class HFModelLink:
    arxiv_id: str
    model_id: str
    downloads: int | None


class HFSource:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        token: str = "",
        timeout: float = 10.0,
    ) -> None:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        self._client = client or httpx.Client(timeout=timeout, headers=headers)

    def find_model_by_paper(self, arxiv_id: str, *, max_results: int = 5) -> list[HFModelLink]:
        """Search HF for models that reference the given arxiv id."""
        params = {"search": f"arxiv:{arxiv_id}", "limit": max_results}
        try:
            resp = self._client.get(f"{HF_API}/models", params=params)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            return []
        if not isinstance(data, list):
            return []
        out: list[HFModelLink] = []
        for m in data[:max_results]:
            if not isinstance(m, dict):
                continue
            mid = m.get("modelId") or m.get("id")
            if not mid:
                continue
            downloads = m.get("downloads") if isinstance(m.get("downloads"), int) else None
            out.append(HFModelLink(arxiv_id=arxiv_id, model_id=str(mid), downloads=downloads))
        return out

    def fetch_model_card(self, model_id: str) -> Evidence | None:
        """Fetch the HF model card README as evidence."""
        url = f"https://huggingface.co/{model_id}/raw/main/README.md"
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            body = resp.text
        except httpx.HTTPError:
            return None
        if not body:
            return None
        return Evidence(
            source=SourceRef(
                kind="huggingface",
                identifier=f"hf:{model_id}",
                title=model_id,
                authors=[model_id.split("/")[0] if "/" in model_id else model_id],
            ),
            content=body[:4000],
            channel="body",
        )

    def close(self) -> None:
        self._client.close()
