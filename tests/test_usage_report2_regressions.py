"""Regression coverage for findings from docs/kullanim-testi-raporu-2.md."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

import pytest

from al_kripto.backtest import BacktestConfig, BacktestEngine, BacktestValidationError, TargetPosition
from al_kripto.market_data import Candle, MarketDataValidationError


class _AlwaysLong:
    def target_position(self, history: Sequence[Candle]) -> TargetPosition:
        del history
        return TargetPosition.LONG


class _AlwaysFlat:
    def target_position(self, history: Sequence[Candle]) -> TargetPosition:
        del history
        return TargetPosition.FLAT


def _candle(
    open_time_ms: int,
    close_time_ms: int,
    *,
    interval: str | None = None,
    price: str = "100",
) -> Candle:
    value = Decimal(price)
    return Candle(
        symbol="BTCUSDT",
        interval=interval,
        open_time_ms=open_time_ms,
        close_time_ms=close_time_ms,
        open=value,
        high=value + Decimal("1"),
        low=value - Decimal("1"),
        close=value,
        volume=Decimal("10"),
        quote_volume=Decimal("1000"),
        trade_count=10,
        taker_buy_base_volume=Decimal("4"),
        taker_buy_quote_volume=Decimal("400"),
    )


def test_y02_extreme_quantity_step_does_not_leak_decimal_invalid_operation() -> None:
    candles = (
        _candle(0, 59_999),
        _candle(60_000, 119_999),
    )
    engine = BacktestEngine(
        BacktestConfig(
            initial_cash=Decimal("1E+25"),
            fee_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
            quantity_step=Decimal("1E-8"),
        ),
        clock_ms=lambda: 120_000,
    )

    result = engine.run(candles, _AlwaysLong())

    assert len(result.fills) == 1
    assert result.final_position_quantity > 0
    assert result.final_position_quantity % Decimal("1E-8") == 0


def test_y03_unlabelled_mixed_duration_series_is_rejected() -> None:
    candles = (
        _candle(0, 59_999),
        _candle(60_000, 3_659_999),
    )

    with pytest.raises(BacktestValidationError, match="actual duration"):
        BacktestEngine(clock_ms=lambda: 4_000_000).run(candles, _AlwaysFlat())


def test_y04_interval_label_must_match_actual_candle_duration() -> None:
    with pytest.raises(MarketDataValidationError, match="interval metadata"):
        _candle(0, 3_599_999, interval="1m")
