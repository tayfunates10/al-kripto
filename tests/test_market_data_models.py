"""Tests for validated market-data models."""

from __future__ import annotations

import unittest
from decimal import Decimal

from al_kripto.market_data import (
    Candle,
    MarketDataValidationError,
    OrderBookLevel,
    OrderBookSnapshot,
    Trade,
)


class CandleTests(unittest.TestCase):
    def test_valid_candle(self) -> None:
        candle = Candle(
            symbol="BTCUSDT",
            open_time_ms=1_000,
            close_time_ms=1_999,
            open=Decimal("100"),
            high=Decimal("110"),
            low=Decimal("95"),
            close=Decimal("105"),
            volume=Decimal("2"),
            quote_volume=Decimal("210"),
            trade_count=8,
            taker_buy_base_volume=Decimal("0.8"),
            taker_buy_quote_volume=Decimal("84"),
        )

        self.assertEqual(candle.close, Decimal("105"))

    def test_rejects_inconsistent_ohlc(self) -> None:
        with self.assertRaises(MarketDataValidationError):
            Candle(
                symbol="BTCUSDT",
                open_time_ms=1_000,
                close_time_ms=1_999,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("95"),
                close=Decimal("105"),
                volume=Decimal("2"),
                quote_volume=Decimal("210"),
                trade_count=8,
                taker_buy_base_volume=Decimal("0.8"),
                taker_buy_quote_volume=Decimal("84"),
            )

    def test_rejects_taker_volume_above_total(self) -> None:
        with self.assertRaises(MarketDataValidationError):
            Candle(
                symbol="BTCUSDT",
                open_time_ms=1_000,
                close_time_ms=1_999,
                open=Decimal("100"),
                high=Decimal("110"),
                low=Decimal("95"),
                close=Decimal("105"),
                volume=Decimal("2"),
                quote_volume=Decimal("210"),
                trade_count=8,
                taker_buy_base_volume=Decimal("3"),
                taker_buy_quote_volume=Decimal("84"),
            )


class TradeTests(unittest.TestCase):
    def test_rejects_non_positive_trade_quantity(self) -> None:
        with self.assertRaises(MarketDataValidationError):
            Trade(
                symbol="ETHUSDT",
                trade_id=1,
                timestamp_ms=10,
                price=Decimal("2000"),
                quantity=Decimal("0"),
                buyer_is_maker=False,
            )


class OrderBookTests(unittest.TestCase):
    def test_spread_is_derived_from_best_levels(self) -> None:
        book = OrderBookSnapshot(
            symbol="BTCUSDT",
            last_update_id=7,
            received_at_ms=123,
            bids=(
                OrderBookLevel(Decimal("100"), Decimal("1")),
                OrderBookLevel(Decimal("99"), Decimal("2")),
            ),
            asks=(
                OrderBookLevel(Decimal("101"), Decimal("1.5")),
                OrderBookLevel(Decimal("102"), Decimal("3")),
            ),
        )

        self.assertEqual(book.best_bid, Decimal("100"))
        self.assertEqual(book.best_ask, Decimal("101"))
        self.assertEqual(book.spread, Decimal("1"))

    def test_rejects_crossed_book(self) -> None:
        with self.assertRaises(MarketDataValidationError):
            OrderBookSnapshot(
                symbol="BTCUSDT",
                last_update_id=7,
                received_at_ms=123,
                bids=(OrderBookLevel(Decimal("101"), Decimal("1")),),
                asks=(OrderBookLevel(Decimal("101"), Decimal("1")),),
            )

    def test_rejects_unsorted_levels(self) -> None:
        with self.assertRaises(MarketDataValidationError):
            OrderBookSnapshot(
                symbol="BTCUSDT",
                last_update_id=7,
                received_at_ms=123,
                bids=(
                    OrderBookLevel(Decimal("99"), Decimal("1")),
                    OrderBookLevel(Decimal("100"), Decimal("1")),
                ),
                asks=(OrderBookLevel(Decimal("101"), Decimal("1")),),
            )


if __name__ == "__main__":
    unittest.main()
