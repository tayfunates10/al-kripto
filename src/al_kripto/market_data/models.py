"""Validated market-data domain models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")
_INTERVAL_PATTERN = re.compile(r"^[1-9]\d*[smhdwM]$")


class MarketDataValidationError(ValueError):
    """Raised when external market data violates required invariants."""


def _validate_symbol(symbol: str) -> None:
    if not _SYMBOL_PATTERN.fullmatch(symbol):
        raise MarketDataValidationError(f"Invalid market symbol: {symbol!r}")


def _require_positive(value: Decimal, field_name: str) -> None:
    if not value.is_finite() or value <= 0:
        raise MarketDataValidationError(f"{field_name} must be finite and > 0.")


def _require_non_negative(value: Decimal, field_name: str) -> None:
    if not value.is_finite() or value < 0:
        raise MarketDataValidationError(f"{field_name} must be finite and >= 0.")


@dataclass(frozen=True, slots=True)
class Candle:
    """One closed or in-progress OHLCV candle with optional source interval metadata."""

    symbol: str
    open_time_ms: int
    close_time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Decimal
    trade_count: int
    taker_buy_base_volume: Decimal
    taker_buy_quote_volume: Decimal
    interval: str | None = None

    def __post_init__(self) -> None:
        _validate_symbol(self.symbol)
        if self.interval is not None and not _INTERVAL_PATTERN.fullmatch(self.interval):
            raise MarketDataValidationError(f"Invalid candle interval: {self.interval!r}")
        if self.open_time_ms < 0 or self.close_time_ms < self.open_time_ms:
            raise MarketDataValidationError("Candle timestamps are invalid.")

        for field_name, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            _require_positive(value, field_name)

        for field_name, value in (
            ("volume", self.volume),
            ("quote_volume", self.quote_volume),
            ("taker_buy_base_volume", self.taker_buy_base_volume),
            ("taker_buy_quote_volume", self.taker_buy_quote_volume),
        ):
            _require_non_negative(value, field_name)

        if self.trade_count < 0:
            raise MarketDataValidationError("trade_count must be >= 0.")
        if self.high < max(self.open, self.close, self.low):
            raise MarketDataValidationError("Candle high is inconsistent with OHLC prices.")
        if self.low > min(self.open, self.close, self.high):
            raise MarketDataValidationError("Candle low is inconsistent with OHLC prices.")
        if self.taker_buy_base_volume > self.volume:
            raise MarketDataValidationError("Taker-buy base volume cannot exceed total volume.")
        if self.taker_buy_quote_volume > self.quote_volume:
            raise MarketDataValidationError("Taker-buy quote volume cannot exceed quote volume.")


@dataclass(frozen=True, slots=True)
class Trade:
    """One aggregate trade."""

    symbol: str
    trade_id: int
    timestamp_ms: int
    price: Decimal
    quantity: Decimal
    buyer_is_maker: bool

    def __post_init__(self) -> None:
        _validate_symbol(self.symbol)
        if self.trade_id < 0:
            raise MarketDataValidationError("trade_id must be >= 0.")
        if self.timestamp_ms < 0:
            raise MarketDataValidationError("Trade timestamp must be >= 0.")
        _require_positive(self.price, "price")
        _require_positive(self.quantity, "quantity")


@dataclass(frozen=True, slots=True)
class OrderBookLevel:
    """One price level in an order-book snapshot."""

    price: Decimal
    quantity: Decimal

    def __post_init__(self) -> None:
        _require_positive(self.price, "price")
        _require_positive(self.quantity, "quantity")


@dataclass(frozen=True, slots=True)
class OrderBookSnapshot:
    """Validated L2 order-book snapshot."""

    symbol: str
    last_update_id: int
    received_at_ms: int
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]

    def __post_init__(self) -> None:
        _validate_symbol(self.symbol)
        if self.last_update_id < 0 or self.received_at_ms < 0:
            raise MarketDataValidationError("Order-book metadata must be non-negative.")
        if not self.bids or not self.asks:
            raise MarketDataValidationError("Order book must contain both bids and asks.")
        if any(
            left.price <= right.price for left, right in zip(self.bids, self.bids[1:], strict=False)
        ):
            raise MarketDataValidationError("Bid levels must be strictly descending by price.")
        if any(
            left.price >= right.price for left, right in zip(self.asks, self.asks[1:], strict=False)
        ):
            raise MarketDataValidationError("Ask levels must be strictly ascending by price.")
        if self.bids[0].price >= self.asks[0].price:
            raise MarketDataValidationError("Order book is crossed or locked.")

    @property
    def best_bid(self) -> Decimal:
        return self.bids[0].price

    @property
    def best_ask(self) -> Decimal:
        return self.asks[0].price

    @property
    def spread(self) -> Decimal:
        return self.best_ask - self.best_bid
