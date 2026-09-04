"""Tests for deterministic and point-in-time-aware SMC primitives."""

from __future__ import annotations

import unittest
from decimal import Decimal

from al_kripto.market_data import Candle
from al_kripto.smc import (
    BreakKind,
    Direction,
    SMCEngine,
    SMCEngineConfig,
    SwingKind,
    detect_fair_value_gaps,
    detect_swings,
)


def candle(
    index: int,
    open_price: str,
    high: str,
    low: str,
    close: str,
    *,
    symbol: str = "BTCUSDT",
) -> Candle:
    return Candle(
        symbol=symbol,
        open_time_ms=index * 60_000,
        close_time_ms=(index * 60_000) + 59_999,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1"),
        quote_volume=Decimal(close),
        trade_count=1,
        taker_buy_base_volume=Decimal("0"),
        taker_buy_quote_volume=Decimal("0"),
    )


class SwingTests(unittest.TestCase):
    def test_swing_records_right_side_confirmation_time(self) -> None:
        candles = (
            candle(0, "9", "10", "8", "9"),
            candle(1, "10", "11", "7", "10"),
            candle(2, "10", "15", "5", "11"),
            candle(3, "11", "12", "6", "10"),
            candle(4, "10", "11", "7", "9"),
        )

        swings = detect_swings(candles, strength=2)

        self.assertEqual(len(swings), 2)
        high = next(swing for swing in swings if swing.kind is SwingKind.HIGH)
        low = next(swing for swing in swings if swing.kind is SwingKind.LOW)
        self.assertEqual(high.index, 2)
        self.assertEqual(low.index, 2)
        self.assertEqual(high.confirmed_index, 4)
        self.assertEqual(high.confirmed_at_ms, candles[4].close_time_ms)


class FairValueGapTests(unittest.TestCase):
    def test_detects_bullish_three_candle_gap(self) -> None:
        candles = (
            candle(0, "95", "100", "90", "98"),
            candle(1, "100", "108", "97", "106"),
            candle(2, "106", "112", "105", "110"),
        )

        gaps = detect_fair_value_gaps(candles)

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].direction, Direction.BULLISH)
        self.assertEqual(gaps[0].lower, Decimal("100"))
        self.assertEqual(gaps[0].upper, Decimal("105"))


class StructureTests(unittest.TestCase):
    def test_detects_sweep_only_after_swing_confirmation(self) -> None:
        candles = (
            candle(0, "9", "10", "8", "9"),
            candle(1, "10", "11", "9", "10"),
            candle(2, "11", "15", "10", "12"),
            candle(3, "12", "13", "11", "12"),
            candle(4, "14", "16", "12", "14"),
        )
        engine = SMCEngine(SMCEngineConfig(swing_strength=1))

        analysis = engine.analyze(candles)

        self.assertEqual(len(analysis.sweeps), 1)
        self.assertEqual(analysis.sweeps[0].direction, Direction.BEARISH)
        self.assertEqual(analysis.sweeps[0].swing_index, 2)
        self.assertEqual(analysis.breaks, ())

    def test_bos_then_opposite_break_is_choch_and_blocks_are_deterministic(self) -> None:
        candles = (
            candle(0, "9", "10", "8", "9"),
            candle(1, "10", "11", "9", "10"),
            candle(2, "11", "15", "10", "12"),
            candle(3, "12", "13", "11", "11.5"),
            candle(4, "12", "16", "11", "16"),
            candle(5, "16", "17", "14", "15"),
            candle(6, "15", "16", "10", "12"),
            candle(7, "12", "14", "11", "13"),
            candle(8, "13", "13", "9", "9"),
        )
        engine = SMCEngine(SMCEngineConfig(swing_strength=1, order_block_lookback=4))

        analysis = engine.analyze(candles)

        self.assertGreaterEqual(len(analysis.breaks), 2)
        self.assertEqual(analysis.breaks[0].kind, BreakKind.BOS)
        self.assertEqual(analysis.breaks[0].direction, Direction.BULLISH)
        bearish_break = next(
            event for event in analysis.breaks if event.direction is Direction.BEARISH
        )
        self.assertEqual(bearish_break.kind, BreakKind.CHOCH)
        bullish_block = next(
            block for block in analysis.order_blocks if block.direction is Direction.BULLISH
        )
        self.assertEqual(bullish_block.index, 3)
        self.assertEqual(bullish_block.confirmed_by_index, 4)

    def test_rejects_mixed_symbols(self) -> None:
        engine = SMCEngine(SMCEngineConfig(swing_strength=1))
        candles = (
            candle(0, "9", "10", "8", "9"),
            candle(1, "9", "10", "8", "9", symbol="ETHUSDT"),
        )

        with self.assertRaises(ValueError):
            engine.analyze(candles)


if __name__ == "__main__":
    unittest.main()
