from __future__ import annotations

from open_fang.memory.working import WorkingBuffer


def test_buffer_keeps_turns_within_cap():
    buf = WorkingBuffer(max_turns=3)
    for i in range(3):
        buf.add("user", f"t{i}")
    assert [t.content for t in buf.turns] == ["t0", "t1", "t2"]
    assert buf.compacted_count == 0
    assert buf.summary() == ""


def test_buffer_compacts_oldest_past_cap():
    buf = WorkingBuffer(max_turns=3)
    for i in range(5):
        buf.add("user", f"t{i}")
    assert [t.content for t in buf.turns] == ["t2", "t3", "t4"]
    assert buf.compacted_count == 2
    assert buf.summary() == "[compacted: 2 earlier turns]"


def test_buffer_summary_grows_over_multiple_compactions():
    buf = WorkingBuffer(max_turns=2)
    for i in range(7):
        buf.add("user", f"t{i}")
    assert buf.compacted_count == 5
    assert [t.content for t in buf.turns] == ["t5", "t6"]
