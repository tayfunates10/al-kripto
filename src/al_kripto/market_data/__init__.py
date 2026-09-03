"""Public market-data interfaces and validated domain models."""

from .base import MarketDataSource
from .binance import (
    BINANCE_PUBLIC_DATA_URL,
    BinanceSpotMarketData,
    MarketDataPayloadError,
    MarketDataTransportError,
)
from .models import (
    Candle,
    MarketDataValidationError,
    OrderBookLevel,
    OrderBookSnapshot,
    Trade,
)

__all__ = [
    "BINANCE_PUBLIC_DATA_URL",
    "BinanceSpotMarketData",
    "Candle",
    "MarketDataPayloadError",
    "MarketDataSource",
    "MarketDataTransportError",
    "MarketDataValidationError",
    "OrderBookLevel",
    "OrderBookSnapshot",
    "Trade",
]
