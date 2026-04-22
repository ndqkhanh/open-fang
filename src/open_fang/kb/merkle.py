"""Merkle-tree chunk hashing for incremental KB reindex (v7.5).

Pattern source: claude-context (Zilliz) — AST + Merkle-tree incremental index.

For OpenFang's text corpus (no AST needed), we chunk at sentence granularity,
hash each chunk, compute a parent root hash. On re-upsert, a chunk whose hash
matches the previous version can skip reindexing.

This is a pure-Python helper; FTS5 reindex hooks land in v8.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str) -> list[str]:
    """Split text into sentence-level chunks, trimmed + filtered empty."""
    if not text:
        return []
    chunks = _SENTENCE_BOUNDARY.split(text.strip())
    return [c.strip() for c in chunks if c.strip()]


def hash_chunk(chunk: str) -> str:
    return hashlib.sha256(chunk.encode("utf-8")).hexdigest()[:16]


@dataclass
class MerkleTree:
    chunks: list[str] = field(default_factory=list)
    chunk_hashes: list[str] = field(default_factory=list)
    root: str = ""

    @classmethod
    def build(cls, text: str) -> MerkleTree:
        chunks = chunk_text(text)
        chunk_hashes = [hash_chunk(c) for c in chunks]
        root = cls._root_hash(chunk_hashes)
        return cls(chunks=chunks, chunk_hashes=chunk_hashes, root=root)

    @staticmethod
    def _root_hash(leaves: list[str]) -> str:
        if not leaves:
            return hashlib.sha256(b"").hexdigest()[:16]
        if len(leaves) == 1:
            return leaves[0]
        combined = hashlib.sha256()
        for h in leaves:
            combined.update(h.encode("utf-8"))
        return combined.hexdigest()[:16]


@dataclass
class ChunkDelta:
    added_indices: list[int]
    removed_indices: list[int]
    unchanged_indices: list[int]

    @property
    def requires_reindex(self) -> bool:
        return bool(self.added_indices or self.removed_indices)

    @property
    def n_unchanged(self) -> int:
        return len(self.unchanged_indices)


def diff_trees(old: MerkleTree, new: MerkleTree) -> ChunkDelta:
    """Return indices (relative to new) that changed vs old.

    An index is 'unchanged' if new.chunk_hashes[i] appears in old.chunk_hashes.
    """
    old_hash_set = set(old.chunk_hashes)
    new_hash_set = set(new.chunk_hashes)

    added = [
        i for i, h in enumerate(new.chunk_hashes) if h not in old_hash_set
    ]
    unchanged = [
        i for i, h in enumerate(new.chunk_hashes) if h in old_hash_set
    ]
    removed = [
        i for i, h in enumerate(old.chunk_hashes) if h not in new_hash_set
    ]
    return ChunkDelta(
        added_indices=added,
        removed_indices=removed,
        unchanged_indices=unchanged,
    )
