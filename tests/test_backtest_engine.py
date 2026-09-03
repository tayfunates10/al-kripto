"""Tests for deterministic backtest event ordering and execution costs."""

from __future__ import annotations

import unittest
from decimal import Decimal

from al_kripto.backtest import (
    BacktestConfig,
    BacktestEngine,
    BacktestValidationError,
    Side,
    TargetPosition,
)
from al_kripto.market_data import Candle


class SequenceStrategy:
    def __init__(self, targets: tuple[TargetPosition, ...]) -> None:
        self._targets = targets
        self.history_lengths: list[int] = []

    def target_position(self, history: tuple[Candle, ...]) -> TargetPosition:
        self.history_lengths.append(len(history))
        index = min(len(history) - 1, len(self._targets) - 1)
        return self._targets[index]


def make_candle(
    index: int,
    open_price: str,
    close_price: str,
    *,
    symbol: str = "BTCUSDT",
) -> Candle:
    opened = Decimal(open_price)
    closed = Decimal(close_price)
    high = max(opened, closed) + Decimal("1")
    low = min(opened, closed) - Decimal("1")
    return Candle(
        symbol=symbol,
        open_time_ms=index * 60_000,
        close_time_ms=((index + 1) * 60_000) - 1,
        open=opened,
        high=high,
        low=low,
        close=closed,
        volume=Decimal("10"),
        quote_volume=Decimal("1000"),
        trade_count=10,
        taker_buy_base_volume=Decimal("4"),
        taker_buy_quote_volume=Decimal("400"),
    )


class BacktestEngineTests(unittest.TestCase):
    def test_signal_on_close_executes_at_next_candle_open(self) -> None:
        candles = (
            make_candle(0, "100", "105"),
            make_candle(1, "110", "111"),
        )
        strategy = SequenceStrategy((TargetPosition.LONG, TargetPosition.LONG))
        result = BacktestEngine(
            BacktestConfig(
                initial_cash=Decimal("1000"),
                fee_bps=Decimal("0"),
                slippage_bps=Decimal("0"),
            )
        ).run(candles, strategy)

        self.assertEqual(len(result.fills), 1)
        self.assertEqual(result.fills[0].side, Side.BUY)
        self.assertEqual(result.fills[0].timestamp_ms, candles[1].open_time_ms)
        self.assertEqual(result.fills[0].reference_price, Decimal("110"))
        self.assertEqual(strategy.history_lengths, [1, 2])

    def test_fee_and_slippage_reduce_round_trip_result(self) -> None:
        candles = (
            make_candle(0, "100", "100"),
            make_candle(1, "100", "110"),
            make_candle(2, "110", "110"),
        )
        targets = (TargetPosition.LONG, TargetPosition.FLAT, TargetPosition.FLAT)
        free = BacktestEngine(
            BacktestConfig(
                initial_cash=Decimal("1000"),
                fee_bps=Decimal("0"),
                slippage_bps=Decimal("0"),
            )
        ).run(candles, SequenceStrategy(targets))
        costly = BacktestEngine(
            BacktestConfig(
                initial_cash=Decimal("1000"),
                fee_bps=Decimal("10"),
                slippage_bps=Decimal("10"),
            )
        ).run(candles, SequenceStrategy(targets))

        self.assertEqual(len(costly.round_trips), 1)
        self.assertGreater(costly.paid_fees, Decimal("0"))
        self.assertLess(costly.final_equity, free.final_equity)
        self.assertLess(costly.round_trips[0].net_pnl, free.round_trips[0].net_pnl)

    def test_drawdown_is_marked_to_market(self) -> None:
        candles = (
            make_candle(0, "100", "100"),
            make_candle(1, "100", "100"),
            make_candle(2, "100", "80"),
        )
        strategy = SequenceStrategy((TargetPosition.LONG, TargetPosition.LONG, TargetPosition.LONG))
        result = BacktestEngine(
            BacktestConfig(
                initial_cash=Decimal("1000"),
                fee_bps=Decimal("0"),
                slippage_bps=Decimal("0"),
            )
        ).run(candles, strategy)

        self.assertEqual(result.max_drawdown, Decimal("0.2"))
        self.assertEqual(result.equity_curve[-1].equity, Decimal("800"))
        self.assertEqual(result.final_position_quantity, Decimal("10"))

    def test_flat_strategy_never_trades(self) -> None:
        candles = (make_candle(0, "100", "101"), make_candle(1, "101", "102"))
        result = BacktestEngine().run(
            candles,
            SequenceStrategy((TargetPosition.FLAT, TargetPosition.FLAT)),
        )

        self.assertEqual(result.fills, ())
        self.assertEqual(result.final_equity, BacktestConfig().initial_cash)
        self.assertEqual(result.win_rate, Decimal("0"))

    def test_rejects_mixed_symbols(self) -> None:
        candles = (
            make_candle(0, "100", "101"),
            make_candle(1, "101", "102", symbol="ETHUSDT"),
        )

        with self.assertRaises(BacktestValidationError):
            BacktestEngine().run(candles, SequenceStrategy((TargetPosition.FLAT,)))

    def test_rejects_overlapping_candles(self) -> None:
        first = make_candle(0, "100", "101")
        overlapping = Candle(
            symbol="BTCUSDT",
            open_time_ms=first.close_time_ms,
            close_time_ms=first.close_time_ms + 60_000,
            open=Decimal("101"),
            high=Decimal("102"),
            low=Decimal("100"),
            close=Decimal("101"),
            volume=Decimal("10"),
            quote_volume=Decimal("1000"),
            trade_count=10,
            taker_buy_base_volume=Decimal("4"),
            taker_buy_quote_volume=Decimal("400"),
        )

        with self.assertRaises(BacktestValidationError):
            BacktestEngine().run(
                (first, overlapping),
                SequenceStrategy((TargetPosition.FLAT,)),
            )

    def test_rejects_empty_series(self) -> None:
        with self.assertRaises(BacktestValidationError):
            BacktestEngine().run((), SequenceStrategy((TargetPosition.FLAT,)))

    def test_rejects_invalid_cost_configuration(self) -> None:
        with self.assertRaises(BacktestValidationError):
            BacktestConfig(fee_bps=Decimal("10000"))
        with self.assertRaises(BacktestValidationError):
            BacktestConfig(slippage_bps=Decimal("-1"))


if __name__ == "__main__":
    unittest.main()
