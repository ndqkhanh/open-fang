"""Permission-gated node parking: a parked node does not block its siblings."""
from __future__ import annotations


class ParkingRegistry:
    """Tracks which node IDs are currently parked awaiting permission."""

    def __init__(self) -> None:
        self._parked: set[str] = set()

    def park(self, node_id: str) -> None:
        self._parked.add(node_id)

    def release(self, node_id: str) -> None:
        self._parked.discard(node_id)

    def is_parked(self, node_id: str) -> bool:
        return node_id in self._parked
