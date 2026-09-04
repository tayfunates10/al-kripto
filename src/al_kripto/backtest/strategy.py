"""Strategy contract used by the backtest engine."""

from __future__ import annotations

from typing import Protocol

from al_kripto.market_data import Candle

from .models import TargetPosition


class BacktestStrategy(Protocol):
    """A strategy that can only request long or flat exposure."""

    def target_position(self, history: tuple[Candle, ...]) -> TargetPosition:
        """Return the desired position after observing the latest closed candle."""
