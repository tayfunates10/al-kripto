"""Regression coverage for findings from docs/kullanim-testi-raporu-2.md."""

from __future__ import annotations

import inspect
from collections.abc import Sequence
from decimal import Decimal

import pytest

from al_kripto.backtest import BacktestConfig, BacktestEngine, BacktestValidationError, TargetPosition
from al_kripto.market_data import (
    Candle,
    MarketDataSource,
    MarketDataValidationError,
    validate_symbol,
)
from al_kripto.onchain import OnChainRegimeConfig
from al_kripto.readiness import ReadinessCheck, ReadinessEvidence, ReadinessValidationError


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


def test_y05_consensus_cannot_exceed_minimum_metric_requirement() -> None:
    with pytest.raises(ValueError, match="consensus_metrics"):
        OnChainRegimeConfig(minimum_metrics=2, consensus_metrics=3)


def test_y07_market_data_protocol_requires_closed_candle_control() -> None:
    parameters = inspect.signature(MarketDataSource.fetch_candles).parameters

    assert "only_closed" in parameters
    assert parameters["only_closed"].default is True


@pytest.mark.parametrize("reference", ["javascript://alert", "file:///etc/passwd"])
def test_y08_unsafe_readiness_reference_schemes_are_rejected(reference: str) -> None:
    with pytest.raises(ReadinessValidationError):
        ReadinessEvidence(
            check=ReadinessCheck.CI_GREEN,
            passed=True,
            reference=reference,
            recorded_at_ms=1_000,
            valid_until_ms=2_000,
        )


def test_y10_symbol_validator_is_public_api() -> None:
    validate_symbol("BTCUSDT")

    with pytest.raises(MarketDataValidationError):
        validate_symbol("btc/usdt")
