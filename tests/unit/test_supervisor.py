from __future__ import annotations

from open_fang.models import Node
from open_fang.supervisor.registry import Supervisor, default_supervisor
from open_fang.supervisor.specialist import (
    Specialist,
    SpecialistContext,
    SpecialistOutcome,
)


class _StubSpecialist(Specialist):
    """Stub that claims the `reason` NodeKind for testing purposes."""

    name = "stub"
    stage = "test"
    handles = {"reason"}

    def __init__(self, output=None, raises=None):  # noqa: ANN001
        self._output = output
        self._raises = raises

    def execute(self, node: Node, context: SpecialistContext):  # noqa: ARG002
        if self._raises is not None:
            raise self._raises
        return self._output


def test_default_supervisor_has_nine_specialists_v4():
    """v4.0 expanded the cohort from 5 → 9."""
    sv = default_supervisor()
    names = sorted(sp.name for sp in sv.specialists)
    assert names == [
        "claim-verifier", "critic", "deep-read", "methodologist",
        "publisher", "research-director", "survey", "synthesis",
        "threat-modeler",
    ]


def test_default_supervisor_roster_is_json_ready():
    roster = default_supervisor().roster()
    assert len(roster) == 9
    for entry in roster:
        assert {"name", "stage", "handles"} <= set(entry)
        assert isinstance(entry["handles"], list)


def test_dispatch_returns_not_handled_for_unknown_kind():
    sv = default_supervisor()
    # `kb.lookup` is a valid NodeKind but not claimed by any default specialist.
    outcome = sv.dispatch(Node(id="x", kind="kb.lookup"), SpecialistContext())
    assert isinstance(outcome, SpecialistOutcome)
    assert outcome.handled is False
    assert outcome.specialist is None


def test_dispatch_to_matching_specialist():
    sv = Supervisor(specialists=[_StubSpecialist(output=["hello"])])
    outcome = sv.dispatch(Node(id="x", kind="reason"), SpecialistContext())
    assert outcome.handled is True
    assert outcome.specialist == "stub"
    assert outcome.output == ["hello"]
    assert sv.stats.per_specialist["stub"].dispatched == 1
    assert sv.stats.per_specialist["stub"].errors == 0


def test_dispatch_isolates_specialist_crash():
    sv = Supervisor(specialists=[_StubSpecialist(raises=RuntimeError("boom"))])
    outcome = sv.dispatch(Node(id="x", kind="reason"), SpecialistContext())
    assert outcome.handled is True
    assert outcome.specialist == "stub"
    assert outcome.error and "RuntimeError: boom" in outcome.error
    assert outcome.output is None
    assert sv.stats.per_specialist["stub"].errors == 1


def test_dispatch_stats_accumulate():
    sv = Supervisor(specialists=[_StubSpecialist(output="x")])
    for _ in range(3):
        sv.dispatch(Node(id="x", kind="reason"), SpecialistContext())
    assert sv.stats.per_specialist["stub"].dispatched == 3


def test_supervisor_empty_specialist_list_handles_nothing():
    sv = Supervisor(specialists=[])
    outcome = sv.dispatch(Node(id="x", kind="search.arxiv"), SpecialistContext())
    assert outcome.handled is False
