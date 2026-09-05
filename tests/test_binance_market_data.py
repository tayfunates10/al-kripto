"""Tests for the Binance Spot public market-data adapter."""

from __future__ import annotations

import unittest
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from al_kripto.market_data import (
    BinanceSpotMarketData,
    MarketDataPayloadError,
    MarketDataValidationError,
)


class FakeTransport:
    def __init__(self, payloads: dict[str, object]) -> None:
        self.payloads = payloads
        self.calls: list[tuple[str, float]] = []

    def __call__(self, url: str, timeout_seconds: float) -> object:
        self.calls.append((url, timeout_seconds))
        path = urlparse(url).path
        return self.payloads[path]


class BinanceSpotMarketDataTests(unittest.TestCase):
    def test_parses_candles_and_query_parameters(self) -> None:
        transport = FakeTransport(
            {
                "/api/v3/klines": [
                    [
                        1000,
                        "100.0",
                        "110.0",
                        "95.0",
                        "105.0",
                        "2.0",
                        1999,
                        "210.0",
                        8,
                        "0.8",
                        "84.0",
                        "0",
                    ]
                ]
            }
        )
        source = BinanceSpotMarketData(transport=transport, clock_ms=lambda: 3000)

        candles = source.fetch_candles(
            "BTCUSDT",
            "1m",
            limit=10,
            start_time_ms=1000,
            end_time_ms=2000,
        )

        self.assertEqual(candles[0].high, Decimal("110.0"))
        query = parse_qs(urlparse(transport.calls[0][0]).query)
        self.assertEqual(query["symbol"], ["BTCUSDT"])
        self.assertEqual(query["interval"], ["1m"])
        self.assertEqual(query["limit"], ["10"])
        self.assertEqual(query["startTime"], ["1000"])
        self.assertEqual(query["endTime"], ["2000"])

    def test_filters_in_progress_candle_by_default(self) -> None:
        transport = FakeTransport(
            {
                "/api/v3/klines": [
                    [1000, "100", "110", "95", "105", "2", 1999, "210", 8, "0.8", "84", "0"],
                    [2000, "105", "111", "104", "110", "2", 2999, "220", 8, "0.8", "88", "0"],
                ]
            }
        )
        source = BinanceSpotMarketData(transport=transport, clock_ms=lambda: 2500)

        candles = source.fetch_candles("BTCUSDT", "1m")

        self.assertEqual([candle.open_time_ms for candle in candles], [1000])

    def test_can_return_in_progress_candle_when_explicitly_requested(self) -> None:
        transport = FakeTransport(
            {
                "/api/v3/klines": [
                    [1000, "100", "110", "95", "105", "2", 1999, "210", 8, "0.8", "84", "0"],
                    [2000, "105", "111", "104", "110", "2", 2999, "220", 8, "0.8", "88", "0"],
                ]
            }
        )
        source = BinanceSpotMarketData(transport=transport, clock_ms=lambda: 2500)

        candles = source.fetch_candles("BTCUSDT", "1m", only_closed=False)

        self.assertEqual([candle.open_time_ms for candle in candles], [1000, 2000])

    def test_parses_aggregate_trades(self) -> None:
        transport = FakeTransport(
            {"/api/v3/aggTrades": [{"a": 10, "p": "100.5", "q": "0.25", "T": 1234, "m": True}]}
        )
        source = BinanceSpotMarketData(transport=transport)

        trades = source.fetch_trades("BTCUSDT", limit=1)

        self.assertEqual(trades[0].trade_id, 10)
        self.assertEqual(trades[0].price, Decimal("100.5"))
        self.assertTrue(trades[0].buyer_is_maker)

    def test_parses_order_book_and_records_receive_time(self) -> None:
        transport = FakeTransport(
            {
                "/api/v3/depth": {
                    "lastUpdateId": 50,
                    "bids": [["100", "1"], ["99", "2"]],
                    "asks": [["101", "1.5"], ["102", "3"]],
                }
            }
        )
        source = BinanceSpotMarketData(transport=transport, clock_ms=lambda: 999)

        book = source.fetch_order_book("BTCUSDT", limit=20)

        self.assertEqual(book.last_update_id, 50)
        self.assertEqual(book.received_at_ms, 999)
        self.assertEqual(book.spread, Decimal("1"))

    def test_rejects_non_chronological_candles(self) -> None:
        transport = FakeTransport(
            {
                "/api/v3/klines": [
                    [2000, "100", "110", "95", "105", "2", 2999, "210", 8, "0.8", "84", "0"],
                    [1000, "100", "110", "95", "105", "2", 1999, "210", 8, "0.8", "84", "0"],
                ]
            }
        )
        source = BinanceSpotMarketData(transport=transport, clock_ms=lambda: 4000)

        with self.assertRaises(MarketDataPayloadError):
            source.fetch_candles("BTCUSDT", "1m")

    def test_rejects_duplicate_candle_open_times(self) -> None:
        duplicate = [1000, "100", "110", "95", "105", "2", 1999, "210", 8, "0.8", "84", "0"]
        transport = FakeTransport({"/api/v3/klines": [duplicate, duplicate.copy()]})
        source = BinanceSpotMarketData(transport=transport, clock_ms=lambda: 4000)

        with self.assertRaises(MarketDataPayloadError):
            source.fetch_candles("BTCUSDT", "1m")

    def test_rejects_invalid_symbol_before_transport(self) -> None:
        transport = FakeTransport({})
        source = BinanceSpotMarketData(transport=transport)

        for fetch in (
            lambda: source.fetch_candles("btcusdt", "1m"),
            lambda: source.fetch_trades(""),
            lambda: source.fetch_order_book("../../etc/passwd"),
        ):
            with self.subTest(fetch=fetch):
                with self.assertRaises(MarketDataValidationError):
                    fetch()
        self.assertEqual(transport.calls, [])

    def test_rejects_malformed_order_book(self) -> None:
        transport = FakeTransport(
            {
                "/api/v3/depth": {
                    "lastUpdateId": 50,
                    "bids": [["100"]],
                    "asks": [["101", "1"]],
                }
            }
        )
        source = BinanceSpotMarketData(transport=transport)

        with self.assertRaises(MarketDataPayloadError):
            source.fetch_order_book("BTCUSDT")

    def test_rejects_invalid_limit_before_transport(self) -> None:
        transport = FakeTransport({})
        source = BinanceSpotMarketData(transport=transport)

        with self.assertRaises(ValueError):
            source.fetch_trades("BTCUSDT", limit=0)
        self.assertEqual(transport.calls, [])


if __name__ == "__main__":
    unittest.main()
