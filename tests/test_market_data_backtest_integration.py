"""Integration checks across market-data and backtest boundaries."""

from __future__ import annotations

import unittest
from collections.abc import Sequence
from urllib.parse import urlparse

from al_kripto.backtest import BacktestEngine, TargetPosition
from al_kripto.market_data import BinanceSpotMarketData, Candle


class _FlatStrategy:
    def target_position(self, history: Sequence[Candle]) -> TargetPosition:
        del history
        return TargetPosition.FLAT


class _Transport:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def __call__(self, url: str, timeout_seconds: float) -> object:
        del timeout_seconds
        self.calls.append(urlparse(url).path)
        return self.payload


class MarketDataBacktestIntegrationTests(unittest.TestCase):
    def test_default_market_data_output_is_directly_backtest_safe(self) -> None:
        transport = _Transport(
            [
                [
                    1_000,
                    "100",
                    "110",
                    "95",
                    "105",
                    "2",
                    60_999,
                    "210",
                    8,
                    "0.8",
                    "84",
                    "0",
                ],
                [
                    61_000,
                    "105",
                    "111",
                    "104",
                    "110",
                    "2",
                    120_999,
                    "220",
                    8,
                    "0.8",
                    "88",
                    "0",
                ],
            ]
        )
        source = BinanceSpotMarketData(transport=transport, clock_ms=lambda: 90_000)
        candles = source.fetch_candles("BTCUSDT", "1m")

        result = BacktestEngine(clock_ms=lambda: 90_000).run(candles, _FlatStrategy())

        self.assertEqual(transport.calls, ["/api/v3/klines"])
        self.assertEqual(len(candles), 1)
        self.assertEqual(candles[0].interval, "1m")
        self.assertEqual(len(result.equity_curve), 1)
        self.assertEqual(result.fills, ())
        self.assertEqual(result.final_position_quantity, 0)


if __name__ == "__main__":
    unittest.main()
