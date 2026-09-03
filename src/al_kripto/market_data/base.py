"""Market-data source contracts."""

from __future__ import annotations

from typing import Protocol

from .models import Candle, OrderBookSnapshot, Trade


class MarketDataSource(Protocol):
    """Provider-independent read-only market-data interface."""

    def fetch_candles(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> list[Candle]:
        """Fetch chronologically ordered candles."""

    def fetch_trades(
        self,
        symbol: str,
        *,
        limit: int = 500,
        start_time_ms: int | None = None,
    ) -> list[Trade]:
        """Fetch aggregate trades."""

    def fetch_order_book(self, symbol: str, *, limit: int = 100) -> OrderBookSnapshot:
        """Fetch a validated order-book snapshot."""
