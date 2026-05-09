"""Deterministic scheduler: walks DAG, dispatches to handlers, retries node-locally.

Permission flow (Phase 5): for nodes whose `risk` is `"medium"` or `"high"`,
the scheduler consults an optional `PermissionBridge` before executing. Bridge
verdicts map to node outcomes:
    allow → execute normally
    park  → node.status = "parked", progresses siblings
    deny  → node.status = "failed" with note "permission denied"
"""
from __future__ import annotations

import time

from ..kb.store import KBStore
from ..memory.sandbox import ToolOutputSandbox
from ..models import DAG, Evidence, Node
from ..observe.tracer import SpanRecorder
from ..permissions.bridge import PermissionBridge
from ..sources.mock import MockSource
from ..sources.router import SearchSource, SourceRouter, from_single
from ..supervisor.registry import Supervisor
from ..supervisor.specialist import SpecialistContext
from .chaos import ChaosInjector
from .parking import ParkingRegistry
from .retries import RetryPolicy


class SchedulerEngine:
    """Walk a DAG, executing ready nodes; supports parking and node-local retry."""

    def __init__(
        self,
        *,
        source: SourceRouter | SearchSource | None = None,
        parking: ParkingRegistry | None = None,
        retry_policy: RetryPolicy | None = None,
        kb: KBStore | None = None,
        permission_bridge: PermissionBridge | None = None,
        chaos: ChaosInjector | None = None,
        supervisor: Supervisor | None = None,
        sandbox: ToolOutputSandbox | None = None,
        sandbox_top_k: int = 5,
    ) -> None:
        self.router = _as_router(source)
        self.parking = parking or ParkingRegistry()
        self.retry_policy = retry_policy or RetryPolicy()
        self.kb: KBStore | None = kb
        self.permission_bridge: PermissionBridge | None = permission_bridge
        self.chaos = chaos or ChaosInjector.from_env()
        self.supervisor: Supervisor | None = supervisor
        self.sandbox = sandbox
        self.sandbox_top_k = sandbox_top_k
        self.last_sandbox_handles: dict[str, str] = {}

    def run(
        self,
        dag: DAG,
        *,
        recorder: SpanRecorder | None = None,
    ) -> tuple[list[Evidence], list[str], list[str]]:
        rec = recorder or SpanRecorder()
        parked: list[str] = []
        failed: list[str] = []
        evidence: list[Evidence] = []
        by_id = {n.id: n for n in dag.nodes}

        def ready(node: Node) -> bool:
            return all(by_id[d].status == "done" for d in node.depends_on)

        for _ in range(len(dag.nodes) * 3):
            progressed = False
            for node in dag.nodes:
                if node.status != "pending":
                    continue
                if not ready(node):
                    continue

                # Static explicit parking overrides permission bridge.
                if self.parking.is_parked(node.id):
                    node.status = "parked"
                    parked.append(node.id)
                    continue

                # Risk-based permission check for medium/high-risk nodes.
                if self.permission_bridge is not None and node.risk != "low":
                    verdict = self.permission_bridge.check(op=node.kind, risk=node.risk)
                    if verdict == "park":
                        node.status = "parked"
                        parked.append(node.id)
                        continue
                    if verdict == "deny":
                        node.status = "failed"
                        node.error = "permission denied"
                        failed.append(node.id)
                        rec.record_error(node, time.monotonic(), PermissionError(node.error))
                        continue

                start = time.monotonic()
                try:
                    out = self._execute_with_retry(node)
                    node.output = out
                    node.status = "done"
                    if isinstance(out, list):
                        evidence.extend(e for e in out if isinstance(e, Evidence))
                    rec.record_ok(node, start)
                except Exception as exc:  # noqa: BLE001 - node-local recovery
                    node.error = str(exc)
                    node.status = "failed"
                    failed.append(node.id)
                    rec.record_error(node, start, exc)
                progressed = True
            if not progressed:
                break
        return evidence, parked, failed

    def _execute_with_retry(self, node: Node) -> object:
        policy = self.retry_policy
        last_exc: BaseException | None = None
        for attempt in range(1, policy.max_attempts + 1):
            try:
                return self._execute(node)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt >= policy.max_attempts:
                    break
                delay = policy.delay_for_attempt(attempt)
                if delay > 0:
                    time.sleep(delay)
        assert last_exc is not None
        raise last_exc

    def _execute(self, node: Node) -> object:
        # Chaos hooks run BEFORE specialist dispatch — fault injection must be
        # visible regardless of who handles the node.
        if (
            node.kind in {"search.arxiv", "search.semantic_scholar", "search.github"}
            and self.chaos.should_fire("network_drop")
        ):
            raise RuntimeError(f"chaos: network_drop on {node.kind}")
        if node.kind == "kb.lookup" and self.chaos.should_fire("memory_drop"):
            return []

        # Supervisor specialists take precedence when wired. Non-claimed kinds
        # fall through to the default handlers below.
        if self.supervisor is not None:
            context = SpecialistContext(
                source_router=self.router,
                kb=self.kb,
            )
            outcome = self.supervisor.dispatch(node, context)
            if outcome.handled:
                if outcome.error is not None:
                    raise RuntimeError(
                        f"specialist {outcome.specialist!r} failed: {outcome.error}"
                    )
                return outcome.output

        if node.kind in {"search.arxiv", "search.semantic_scholar", "search.github"}:
            query = node.args.get("query", "")
            max_results = int(node.args.get("max_results", 5))
            results = self.router.search(node.kind, query, max_results=max_results)
            return self._maybe_sandbox(node, query, results)
        if node.kind == "kb.lookup":
            if self.kb is None:
                return []
            query = node.args.get("query", "")
            limit = int(node.args.get("limit", 5))
            return self.kb.search(query, limit=limit)
        return []


    def _maybe_sandbox(
        self,
        node: Node,
        query: str,
        results: list[Evidence],
    ) -> list[Evidence]:
        """v7.0 — if the payload is above threshold, sandbox it and return top-k."""
        if self.sandbox is None or not self.sandbox.should_sandbox(results):
            return results
        handle, top_k = self.sandbox.sandbox(
            evidence=results,
            source_kind=node.kind,
            query=query,
            top_k=self.sandbox_top_k,
        )
        self.last_sandbox_handles[node.id] = handle
        return top_k


def _as_router(source: SourceRouter | SearchSource | None) -> SourceRouter:
    if source is None:
        return from_single(MockSource())
    if isinstance(source, SourceRouter):
        return source
    return from_single(source)
