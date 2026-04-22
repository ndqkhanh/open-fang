from __future__ import annotations

import time

from open_fang.models import Node
from open_fang.observe.tracer import SpanRecorder


def test_recorder_captures_ok_and_error():
    rec = SpanRecorder()
    node_a = Node(id="A", kind="kb.lookup")
    node_b = Node(id="B", kind="search.arxiv")
    rec.record_ok(node_a, time.monotonic())
    rec.record_error(node_b, time.monotonic(), RuntimeError("boom"))
    assert len(rec.spans) == 2
    verdicts = [s.verdict for s in rec.spans]
    assert verdicts == ["ok", "error"]
    assert rec.spans[1].error == "boom"
