from __future__ import annotations

from pathlib import Path

import pytest

from open_fang.memory.fang import FANGLoader


def test_fang_loads_from_path(tmp_fang: Path):
    loader = FANGLoader(path=tmp_fang)
    assert "FANG seed" in loader.load()


def test_fang_returns_empty_when_missing(tmp_path: Path):
    assert FANGLoader(path=tmp_path / "nope.md").load() == ""


def test_fang_rejects_oversize(tmp_path: Path):
    big = tmp_path / "FANG.md"
    big.write_text("x" * 20_000, encoding="utf-8")
    with pytest.raises(ValueError):
        FANGLoader(path=big, max_bytes=16_000).load()
