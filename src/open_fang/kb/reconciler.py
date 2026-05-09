"""Edge reconciler (v8.3) — diff + expire stale self-wired edges on re-upsert.

Pattern source: GBrain's reconciler ("stale links are reconciled when pages
are edited"). Domain-swapped to OpenFang's edges table.

Key invariant (CC-3 from v8-plan.md): **manually inserted edges are never
touched**. The reconciler only operates on edges whose `provenance` is a
self-wire label (or missing — in which case we assume manual).

Since the existing v1 edges table has no `provenance` column, v8.3 runs a
one-off migration (ALTER TABLE ADD COLUMN provenance TEXT) on open. Existing
rows get NULL provenance and are thus safe from auto-deletion.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .self_wire import InferredEdge
from .store import KBStore

_SELF_WIRE_PROVENANCE_PREFIX = "self-wire:"


@dataclass
class ReconciliationReport:
    kept: int = 0
    added: int = 0
    removed: int = 0
    preserved_manual: int = 0
    added_edges: list[tuple[str, str, str]] = field(default_factory=list)
    removed_edges: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed)


def ensure_provenance_column(kb: KBStore) -> None:
    """Idempotent migration. Adds `provenance TEXT` to edges if missing."""
    cols = [
        r["name"]
        for r in kb._c.execute("PRAGMA table_info(edges)").fetchall()  # noqa: SLF001
    ]
    if "provenance" not in cols:
        kb._c.execute("ALTER TABLE edges ADD COLUMN provenance TEXT")  # noqa: SLF001
        kb._c.commit()


def reconcile_self_wired_edges(
    kb: KBStore,
    *,
    paper_id: str,
    new_edges: list[InferredEdge],
) -> ReconciliationReport:
    """Replace existing self-wire edges from `paper_id` with `new_edges`.

    - Manual edges (NULL or non-self-wire provenance) are preserved.
    - Self-wire edges present in old but missing in new → removed.
    - Self-wire edges present in new but missing in old → added.
    - Self-wire edges present in both → kept.
    """
    ensure_provenance_column(kb)

    # Fetch current self-wire edges for this source paper.
    existing_rows = kb._c.execute(  # noqa: SLF001
        """
        SELECT dst_paper_id, kind, COALESCE(provenance, '') AS provenance
        FROM edges WHERE src_paper_id = ?
        """,
        (paper_id,),
    ).fetchall()

    manual: list[tuple[str, str]] = []
    self_wired_existing: set[tuple[str, str]] = set()
    for r in existing_rows:
        prov = r["provenance"] or ""
        key = (r["dst_paper_id"], r["kind"])
        if prov.startswith(_SELF_WIRE_PROVENANCE_PREFIX):
            self_wired_existing.add(key)
        else:
            manual.append(key)

    new_keyed: dict[tuple[str, str], InferredEdge] = {
        (e.dst_paper_id, e.kind): e for e in new_edges
    }

    report = ReconciliationReport(preserved_manual=len(manual))

    # Remove stale self-wired edges.
    for dst, kind in self_wired_existing - new_keyed.keys():
        kb._c.execute(  # noqa: SLF001
            """
            DELETE FROM edges
            WHERE src_paper_id = ? AND dst_paper_id = ? AND kind = ?
              AND COALESCE(provenance, '') LIKE ?
            """,
            (paper_id, dst, kind, f"{_SELF_WIRE_PROVENANCE_PREFIX}%"),
        )
        report.removed += 1
        report.removed_edges.append((paper_id, dst, kind))

    # Add new self-wired edges (upsert with provenance).
    for key, edge in new_keyed.items():
        if key in self_wired_existing:
            report.kept += 1
            continue
        dst, kind = key
        kb._c.execute(  # noqa: SLF001
            """
            INSERT OR IGNORE INTO edges
              (src_paper_id, dst_paper_id, kind, provenance)
            VALUES (?, ?, ?, ?)
            """,
            (paper_id, dst, kind, edge.provenance or f"{_SELF_WIRE_PROVENANCE_PREFIX}unknown"),
        )
        report.added += 1
        report.added_edges.append((paper_id, dst, kind))

    kb._c.commit()  # noqa: SLF001
    return report
