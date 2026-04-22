"""Embedder protocol + stdlib-only HashEmbedder (v7.1).

Production uses `HFEmbedder` (sentence-transformers/bge-small-en, ~64MB) or
`OpenAIEmbedder` (text-embedding-3-small). Tests use `HashEmbedder` — a
deterministic hash-based fallback that produces distinguishable vectors
without an ML dependency.

Vector storage: float32 little-endian packed into BLOB (via struct).
"""
from __future__ import annotations

import hashlib
import struct
from typing import Protocol


class Embedder(Protocol):
    """Minimal interface. `dim` is the embedding dimension; `model_id`
    is a string the KB stores alongside the vector so a later re-embed
    with a different model doesn't silently compare across schemas."""

    dim: int
    model_id: str

    def embed(self, text: str) -> list[float]: ...


class HashEmbedder:
    """Stable hash-based bag-of-words vector. No ML dependency.

    Each token hashes (md5) to a fixed bucket; buckets accumulate token
    frequency; the vector is L2-normalized. Tests rely on determinism across
    Python invocations — stdlib `hash()` is not stable, so we use md5.
    """

    def __init__(self, *, dim: int = 64, model_id: str = "hash-bow-v1") -> None:
        self.dim = dim
        self.model_id = model_id

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = (text or "").lower().split()
        if not tokens:
            return vec
        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dim
            vec[bucket] += 1.0
        norm = sum(v * v for v in vec) ** 0.5
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


def pack_vector(vec: list[float]) -> bytes:
    """Serialize float32 little-endian."""
    return struct.pack(f"<{len(vec)}f", *vec)


def unpack_vector(blob: bytes, dim: int) -> list[float]:
    return list(struct.unpack(f"<{dim}f", blob))


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity. Vectors must be same length."""
    if len(a) != len(b):
        raise ValueError(f"dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
