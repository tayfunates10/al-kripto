"""Backtest configuration and immutable result models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

_BPS_DENOMINATOR = Decimal("10000")
_ZERO = Decimal("0")
_ONE = Decimal("1")


class BacktestValidationError(ValueError):
    """Raised when a backtest input or strategy output violates invariants."""


class TargetPosition(StrEnum):
    """Supported MVP target positions."""

    FLAT = "flat"
    LONG = "long"


class Side(StrEnum):
    """Execution side for a simulated fill."""

    BUY = "buy"
    SELL = "sell"


def _require_finite_non_negative(value: Decimal, field_name: str) -> None:
    if not value.is_finite() or value < _ZERO:
        raise BacktestValidationError(f"{field_name} must be finite and >= 0.")


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Execution assumptions shared by one backtest run."""

    initial_cash: Decimal = Decimal("10000")
    fee_bps: Decimal = Decimal("10")
    slippage_bps: Decimal = Decimal("5")

    def __post_init__(self) -> None:
        if not self.initial_cash.is_finite() or self.initial_cash <= _ZERO:
            raise BacktestValidationError("initial_cash must be finite and > 0.")
        for field_name, value in (
            ("fee_bps", self.fee_bps),
            ("slippage_bps", self.slippage_bps),
        ):
            _require_finite_non_negative(value, field_name)
            if value >= _BPS_DENOMINATOR:
                raise BacktestValidationError(f"{field_name} must be < 10000.")

    @property
    def fee_rate(self) -> Decimal:
        return self.fee_bps / _BPS_DENOMINATOR

    @property
    def slippage_rate(self) -> Decimal:
        return self.slippage_bps / _BPS_DENOMINATOR


@dataclass(frozen=True, slots=True)
class Fill:
    """One simulated execution at a candle open."""

    side: Side
    timestamp_ms: int
    quantity: Decimal
    reference_price: Decimal
    execution_price: Decimal
    notional: Decimal
    fee: Decimal

    def __post_init__(self) -> None:
        if self.timestamp_ms < 0:
            raise BacktestValidationError("Fill timestamp must be >= 0.")
        for field_name, value in (
            ("quantity", self.quantity),
            ("reference_price", self.reference_price),
            ("execution_price", self.execution_price),
            ("notional", self.notional),
        ):
            if not value.is_finite() or value <= _ZERO:
                raise BacktestValidationError(f"{field_name} must be finite and > 0.")
        _require_finite_non_negative(self.fee, "fee")


@dataclass(frozen=True, slots=True)
class RoundTrip:
    """One completed long position from buy fill to sell fill."""

    entry: Fill
    exit: Fill
    gross_pnl: Decimal
    net_pnl: Decimal

    def __post_init__(self) -> None:
        if self.entry.side is not Side.BUY or self.exit.side is not Side.SELL:
            raise BacktestValidationError("RoundTrip requires BUY entry and SELL exit.")
        if self.exit.timestamp_ms <= self.entry.timestamp_ms:
            raise BacktestValidationError("RoundTrip exit must be later than entry.")
        if not self.gross_pnl.is_finite() or not self.net_pnl.is_finite():
            raise BacktestValidationError("RoundTrip PnL must be finite.")


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """End-of-candle marked-to-market portfolio state."""

    timestamp_ms: int
    equity: Decimal
    drawdown: Decimal

    def __post_init__(self) -> None:
        if self.timestamp_ms < 0:
            raise BacktestValidationError("Equity timestamp must be >= 0.")
        if not self.equity.is_finite() or self.equity < _ZERO:
            raise BacktestValidationError("equity must be finite and >= 0.")
        if not self.drawdown.is_finite() or not _ZERO <= self.drawdown <= _ONE:
            raise BacktestValidationError("drawdown must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Deterministic summary of a completed backtest run."""

    initial_cash: Decimal
    final_cash: Decimal
    final_position_quantity: Decimal
    final_equity: Decimal
    paid_fees: Decimal
    max_drawdown: Decimal
    fills: tuple[Fill, ...]
    round_trips: tuple[RoundTrip, ...]
    equity_curve: tuple[EquityPoint, ...]

    @property
    def total_return(self) -> Decimal:
        return (self.final_equity / self.initial_cash) - _ONE

    @property
    def win_rate(self) -> Decimal:
        if not self.round_trips:
            return _ZERO
        wins = sum(1 for trade in self.round_trips if trade.net_pnl > _ZERO)
        return Decimal(wins) / Decimal(len(self.round_trips))
