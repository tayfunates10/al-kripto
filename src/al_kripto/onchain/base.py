"""Provider-independent on-chain data contract."""

from __future__ import annotations

from typing import Protocol

from .models import OnChainSnapshot


class OnChainDataSource(Protocol):
    """Read-only source capable of returning a point-in-time on-chain snapshot."""

    def fetch_snapshot(self, asset: str, *, as_of_ms: int) -> OnChainSnapshot:
        """Return observations that were available no later than the requested time."""
        ...
