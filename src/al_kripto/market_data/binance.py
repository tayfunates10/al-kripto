"""Read-only Binance Spot public market-data adapter."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation
from itertools import pairwise
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import (
    Candle,
    MarketDataValidationError,
    OrderBookLevel,
    OrderBookSnapshot,
    Trade,
    _validate_symbol,
)

BINANCE_PUBLIC_DATA_URL = "https://data-api.binance.vision"
_SUPPORTED_INTERVALS = frozenset(
    {
        "1s",
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    }
)

Transport = Callable[[str, float], object]
Clock = Callable[[], int]


class MarketDataTransportError(RuntimeError):
    """Raised when public market data cannot be retrieved or decoded."""


class MarketDataPayloadError(MarketDataValidationError):
    """Raised when a provider payload has an unexpected shape or type."""


def _default_transport(url: str, timeout_seconds: float) -> object:
    request = Request(url, headers={"User-Agent": "al-kripto/0.1"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except OSError as error:
        raise MarketDataTransportError(f"Market-data request failed: {error}") from error

    try:
        payload: object = json.loads(raw)
    except json.JSONDecodeError as error:
        raise MarketDataTransportError("Market-data response was not valid JSON.") from error
    return payload


def _default_clock_ms() -> int:
    return time.time_ns() // 1_000_000


class BinanceSpotMarketData:
    """Minimal dependency-free adapter for Binance Spot public market data."""

    def __init__(
        self,
        *,
        base_url: str = BINANCE_PUBLIC_DATA_URL,
        timeout_seconds: float = 10.0,
        transport: Transport = _default_transport,
        clock_ms: Clock = _default_clock_ms,
    ) -> None:
        normalized_url = base_url.rstrip("/")
        if not normalized_url.startswith("https://"):
            raise ValueError("base_url must use HTTPS.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0.")
        self._base_url = normalized_url
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._clock_ms = clock_ms

    def fetch_candles(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        only_closed: bool = True,
    ) -> list[Candle]:
        _validate_symbol(symbol)
        if interval not in _SUPPORTED_INTERVALS:
            raise ValueError(f"Unsupported Binance interval: {interval!r}")
        _validate_limit(limit, maximum=1000)
        _validate_optional_timestamp(start_time_ms, "start_time_ms")
        _validate_optional_timestamp(end_time_ms, "end_time_ms")
        if start_time_ms is not None and end_time_ms is not None and start_time_ms > end_time_ms:
            raise ValueError("start_time_ms cannot be later than end_time_ms.")

        payload = self._get(
            "/api/v3/klines",
            {
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
            },
        )
        rows = _as_list(payload, "klines")
        candles = [_parse_candle(symbol, row) for row in rows]
        _ensure_chronological(
            candles,
            key=lambda item: item.open_time_ms,
            label="candles",
            strict=True,
        )

        if only_closed:
            as_of_ms = self._clock_ms()
            if as_of_ms < 0:
                raise MarketDataPayloadError("market-data clock must be non-negative.")
            candles = [candle for candle in candles if candle.close_time_ms <= as_of_ms]
        return candles

    def fetch_trades(
        self,
        symbol: str,
        *,
        limit: int = 500,
        start_time_ms: int | None = None,
    ) -> list[Trade]:
        _validate_symbol(symbol)
        _validate_limit(limit, maximum=1000)
        _validate_optional_timestamp(start_time_ms, "start_time_ms")
        payload = self._get(
            "/api/v3/aggTrades",
            {"symbol": symbol, "limit": limit, "startTime": start_time_ms},
        )
        rows = _as_list(payload, "aggregate trades")
        trades = [_parse_trade(symbol, row) for row in rows]
        _ensure_chronological(
            trades,
            key=lambda item: item.timestamp_ms,
            label="trades",
            strict=False,
        )
        return trades

    def fetch_order_book(self, symbol: str, *, limit: int = 100) -> OrderBookSnapshot:
        _validate_symbol(symbol)
        _validate_limit(limit, maximum=5000)
        payload = _as_mapping(
            self._get("/api/v3/depth", {"symbol": symbol, "limit": limit}),
            "order book",
        )
        bids = tuple(_parse_level(row, "bid") for row in _as_list(payload.get("bids"), "bids"))
        asks = tuple(_parse_level(row, "ask") for row in _as_list(payload.get("asks"), "asks"))
        return OrderBookSnapshot(
            symbol=symbol,
            last_update_id=_as_int(payload.get("lastUpdateId"), "lastUpdateId"),
            received_at_ms=self._clock_ms(),
            bids=bids,
            asks=asks,
        )

    def _get(self, path: str, params: Mapping[str, object | None]) -> object:
        query = urlencode({key: value for key, value in params.items() if value is not None})
        url = f"{self._base_url}{path}?{query}"
        try:
            return self._transport(url, self._timeout_seconds)
        except MarketDataTransportError:
            raise
        except (OSError, ValueError) as error:
            raise MarketDataTransportError(f"Market-data transport failed: {error}") from error


def _validate_limit(limit: int, *, maximum: int) -> None:
    if not 1 <= limit <= maximum:
        raise ValueError(f"limit must be between 1 and {maximum}.")


def _validate_optional_timestamp(value: int | None, field_name: str) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{field_name} must be >= 0.")


def _as_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise MarketDataPayloadError(f"{label} payload must be a list.")
    return value


def _as_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise MarketDataPayloadError(f"{label} payload must be an object.")
    if not all(isinstance(key, str) for key in value):
        raise MarketDataPayloadError(f"{label} payload keys must be strings.")
    return value


def _as_decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise MarketDataPayloadError(f"{field_name} must be numeric.")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise MarketDataPayloadError(f"{field_name} must be numeric.") from error
    if not parsed.is_finite():
        raise MarketDataPayloadError(f"{field_name} must be finite.")
    return parsed


def _as_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or value is None:
        raise MarketDataPayloadError(f"{field_name} must be an integer.")
    try:
        parsed = int(str(value))
    except ValueError as error:
        raise MarketDataPayloadError(f"{field_name} must be an integer.") from error
    return parsed


def _as_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise MarketDataPayloadError(f"{field_name} must be a boolean.")
    return value


def _parse_candle(symbol: str, payload: object) -> Candle:
    row = _as_list(payload, "kline row")
    if len(row) < 11:
        raise MarketDataPayloadError("Kline row must contain at least 11 fields.")
    return Candle(
        symbol=symbol,
        open_time_ms=_as_int(row[0], "open time"),
        open=_as_decimal(row[1], "open"),
        high=_as_decimal(row[2], "high"),
        low=_as_decimal(row[3], "low"),
        close=_as_decimal(row[4], "close"),
        volume=_as_decimal(row[5], "volume"),
        close_time_ms=_as_int(row[6], "close time"),
        quote_volume=_as_decimal(row[7], "quote volume"),
        trade_count=_as_int(row[8], "trade count"),
        taker_buy_base_volume=_as_decimal(row[9], "taker buy base volume"),
        taker_buy_quote_volume=_as_decimal(row[10], "taker buy quote volume"),
    )


def _parse_trade(symbol: str, payload: object) -> Trade:
    row = _as_mapping(payload, "aggregate trade")
    return Trade(
        symbol=symbol,
        trade_id=_as_int(row.get("a"), "aggregate trade id"),
        price=_as_decimal(row.get("p"), "trade price"),
        quantity=_as_decimal(row.get("q"), "trade quantity"),
        timestamp_ms=_as_int(row.get("T"), "trade timestamp"),
        buyer_is_maker=_as_bool(row.get("m"), "buyer-is-maker"),
    )


def _parse_level(payload: object, side: str) -> OrderBookLevel:
    row = _as_list(payload, f"{side} level")
    if len(row) != 2:
        raise MarketDataPayloadError(f"{side} level must contain price and quantity.")
    return OrderBookLevel(
        price=_as_decimal(row[0], f"{side} price"),
        quantity=_as_decimal(row[1], f"{side} quantity"),
    )


def _ensure_chronological[T](
    items: list[T],
    *,
    key: Callable[[T], int],
    label: str,
    strict: bool,
) -> None:
    if strict:
        invalid = any(key(left) >= key(right) for left, right in pairwise(items))
    else:
        invalid = any(key(left) > key(right) for left, right in pairwise(items))
    if invalid:
        qualifier = "strictly chronological" if strict else "chronological"
        raise MarketDataPayloadError(f"{label} must be {qualifier}.")
