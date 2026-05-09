"""Runtime adapters for external orchestration frameworks (v5.5)."""
from .multica import MulticaAdapter, MulticaEvent, MulticaMessage

__all__ = ["MulticaAdapter", "MulticaEvent", "MulticaMessage"]
