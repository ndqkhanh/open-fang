from __future__ import annotations

from open_fang.kb.store import KBStore
from open_fang.models import Evidence, SourceRef
from open_fang.sources.delta import (
    apply_delta_mode,
    content_sha256,
    delta_stub,
    resolve_delta,
)


def _ev(identifier: str, content: str) -> Evidence:
    return Evidence(
        source=SourceRef(kind="arxiv", identifier=identifier, title=identifier),
        content=content,
    )


def test_content_sha256_is_stable():
    a = content_sha256("ReWOO decouples reasoning")
    b = content_sha256("ReWOO decouples reasoning")
    assert a == b
    assert len(a) == 16


def test_delta_stub_empties_content_and_sets_handle():
    ev = _ev("arxiv:x", "long body here")
    stub = delta_stub(ev)
    assert stub.delta_mode is True
    assert stub.delta_handle == "arxiv:x"
    assert stub.content == ""


def test_apply_delta_mode_identifies_known_paper():
    kb = KBStore(db_path=":memory:").open()
    content = "ReWOO decouples reasoning from observations."
    kb.upsert_paper(
        SourceRef(kind="arxiv", identifier="arxiv:x", title="x"), abstract=content
    )
    incoming = [_ev("arxiv:x", content)]  # same content
    out, delta_ids = apply_delta_mode(incoming, kb=kb)
    assert len(out) == 1
    assert out[0].delta_mode is True
    assert delta_ids == ["arxiv:x"]


def test_apply_delta_mode_passes_through_changed_content():
    kb = KBStore(db_path=":memory:").open()
    kb.upsert_paper(
        SourceRef(kind="arxiv", identifier="arxiv:x", title="x"),
        abstract="ORIGINAL content",
    )
    incoming = [_ev("arxiv:x", "UPDATED content")]
    out, delta_ids = apply_delta_mode(incoming, kb=kb)
    assert out[0].delta_mode is False
    assert delta_ids == []


def test_apply_delta_mode_passes_through_new_paper():
    kb = KBStore(db_path=":memory:").open()
    incoming = [_ev("arxiv:new", "new content")]
    out, delta_ids = apply_delta_mode(incoming, kb=kb)
    assert out[0].delta_mode is False
    assert delta_ids == []


def test_resolve_delta_fetches_full_paper():
    kb = KBStore(db_path=":memory:").open()
    kb.upsert_paper(
        SourceRef(kind="arxiv", identifier="arxiv:x", title="x"),
        abstract="full content here",
    )
    stub = delta_stub(_ev("arxiv:x", ""))
    resolved = resolve_delta(stub, kb)
    assert resolved is not None
    assert "full content here" in resolved.content


def test_resolve_delta_returns_none_for_non_stub():
    kb = KBStore(db_path=":memory:").open()
    ev = _ev("arxiv:x", "some content")
    assert resolve_delta(ev, kb) is None
