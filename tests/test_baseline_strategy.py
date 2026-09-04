"""Tests for the first deterministic baseline strategy."""

from __future__ import annotations

import unittest
from decimal import Decimal

from al_kripto.backtest import TargetPosition
from al_kripto.market_data import Candle
from al_kripto.strategy import (
    BaselineStrategy,
    BaselineStrategyConfig,
    mean_absolute_return,
    simple_moving_average,
    volume_weighted_price,
)


def candle(index: int, close: str, *, volume: str = "1") -> Candle:
    price = Decimal(close)
    return Candle(
        symbol="BTCUSDT",
        open_time_ms=index * 60_000,
        close_time_ms=(index * 60_000) + 59_999,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Decimal(volume),
        quote_volume=price * Decimal(volume),
        trade_count=1,
        taker_buy_base_volume=Decimal("0"),
        taker_buy_quote_volume=Decimal("0"),
    )


class IndicatorTests(unittest.TestCase):
    def test_simple_moving_average(self) -> None:
        self.assertEqual(
            simple_moving_average((Decimal("1"), Decimal("2"), Decimal("3"))),
            Decimal("2"),
        )

    def test_volume_weighted_price(self) -> None:
        candles = (candle(0, "100", volume="1"), candle(1, "110", volume="3"))
        self.assertEqual(volume_weighted_price(candles), Decimal("107.5"))

    def test_zero_volume_vwap_returns_none(self) -> None:
        candles = (candle(0, "100", volume="0"), candle(1, "110", volume="0"))
        self.assertIsNone(volume_weighted_price(candles))

    def test_mean_absolute_return(self) -> None:
        value = mean_absolute_return((Decimal("100"), Decimal("110"), Decimal("99")))
        self.assertEqual(value, Decimal("0.10"))


class BaselineStrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = BaselineStrategyConfig(
            fast_window=2,
            slow_window=4,
            vwap_window=3,
            volatility_window=3,
            max_mean_absolute_return=Decimal("0.20"),
        )
        self.strategy = BaselineStrategy(self.config)

    def test_stays_flat_until_minimum_history(self) -> None:
        history = (candle(0, "100"), candle(1, "101"), candle(2, "102"))
        self.assertEqual(self.strategy.target_position(history), TargetPosition.FLAT)

    def test_enters_long_when_all_filters_agree(self) -> None:
        history = tuple(
            candle(index, close)
            for index, close in enumerate(("100", "100", "101", "103", "106"))
        )
        self.assertEqual(self.strategy.target_position(history), TargetPosition.LONG)

    def test_stays_flat_when_trend_filter_fails(self) -> None:
        history = tuple(
            candle(index, close)
            for index, close in enumerate(("106", "105", "103", "101", "100"))
        )
        self.assertEqual(self.strategy.target_position(history), TargetPosition.FLAT)

    def test_stays_flat_when_volatility_is_too_high(self) -> None:
        strategy = BaselineStrategy(
            BaselineStrategyConfig(
                fast_window=2,
                slow_window=4,
                vwap_window=3,
                volatility_window=3,
                max_mean_absolute_return=Decimal("0.01"),
            )
        )
        history = tuple(
            candle(index, close)
            for index, close in enumerate(("100", "100", "101", "103", "106"))
        )
        self.assertEqual(strategy.target_position(history), TargetPosition.FLAT)

    def test_stays_flat_without_volume(self) -> None:
        history = tuple(
            candle(index, close, volume="0")
            for index, close in enumerate(("100", "100", "101", "103", "106"))
        )
        self.assertEqual(self.strategy.target_position(history), TargetPosition.FLAT)

    def test_config_rejects_invalid_window_order(self) -> None:
        with self.assertRaises(ValueError):
            BaselineStrategyConfig(fast_window=10, slow_window=10)


if __name__ == "__main__":
    unittest.main()
