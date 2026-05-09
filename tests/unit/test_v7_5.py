from __future__ import annotations

from open_fang.kb.merkle import (
    MerkleTree,
    chunk_text,
    diff_trees,
    hash_chunk,
)


def test_chunk_text_splits_on_sentence_boundaries():
    out = chunk_text("One sentence. Two! Three?")
    assert out == ["One sentence.", "Two!", "Three?"]


def test_chunk_text_handles_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_hash_chunk_deterministic():
    assert hash_chunk("hello") == hash_chunk("hello")
    assert hash_chunk("hello") != hash_chunk("world")


def test_tree_build_populates_root_and_hashes():
    t = MerkleTree.build("A. B. C.")
    assert len(t.chunks) == 3
    assert len(t.chunk_hashes) == 3
    assert t.root != ""


def test_tree_identical_text_same_root():
    a = MerkleTree.build("A. B. C.")
    b = MerkleTree.build("A. B. C.")
    assert a.root == b.root


def test_tree_different_text_different_root():
    a = MerkleTree.build("A. B. C.")
    b = MerkleTree.build("A. B. D.")
    assert a.root != b.root


def test_diff_identical_trees_zero_delta():
    a = MerkleTree.build("Alpha. Beta. Gamma.")
    b = MerkleTree.build("Alpha. Beta. Gamma.")
    d = diff_trees(a, b)
    assert d.added_indices == []
    assert d.removed_indices == []
    assert d.n_unchanged == 3
    assert d.requires_reindex is False


def test_diff_one_sentence_change():
    a = MerkleTree.build("Alpha. Beta. Gamma.")
    b = MerkleTree.build("Alpha. Delta. Gamma.")
    d = diff_trees(a, b)
    assert len(d.added_indices) == 1  # "Delta." is new
    assert len(d.removed_indices) == 1  # "Beta." was removed
    assert d.n_unchanged == 2
    assert d.requires_reindex is True


def test_diff_full_replacement():
    a = MerkleTree.build("Old content. More old.")
    b = MerkleTree.build("Totally new. Different entirely.")
    d = diff_trees(a, b)
    assert d.n_unchanged == 0
    assert len(d.added_indices) == 2
    assert len(d.removed_indices) == 2
