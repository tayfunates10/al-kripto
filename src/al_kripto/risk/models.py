"""Validated models for the central risk gate."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")
_ZERO = Decimal("0")
_ONE = Decimal("1")


class RiskValidationError(ValueError):
    """Raised when a risk request, limit, or portfolio context is inconsistent."""


class RiskDecision(StrEnum):
    """Possible outcomes of the central risk gate."""

    APPROVE = "approve"
    REDUCE = "reduce"
    REJECT = "reject"


class RiskReason(StrEnum):
    """Auditable reasons for reducing or rejecting an exposure increase."""

    KILL_SWITCH = "kill_switch"
    RECONCILIATION_ERROR = "reconciliation_error"
    STALE_MARKET_DATA = "stale_market_data"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    DRAWDOWN_LIMIT = "drawdown_limit"
    MAX_OPEN_POSITIONS = "max_open_positions"
    CORRELATION_LIMIT = "correlation_limit"
    TRADE_RISK_LIMIT = "trade_risk_limit"
    TOTAL_EXPOSURE_LIMIT = "total_exposure_limit"
    SYMBOL_EXPOSURE_LIMIT = "symbol_exposure_limit"


def _require_fraction(value: Decimal, field_name: str, *, allow_zero: bool = False) -> None:
    lower_ok = value >= _ZERO if allow_zero else value > _ZERO
    if not value.is_finite() or not lower_ok or value > _ONE:
        lower = "0" if allow_zero else "0 (exclusive)"
        raise RiskValidationError(f"{field_name} must be finite and between {lower} and 1.")


def _require_positive(value: Decimal, field_name: str) -> None:
    if not value.is_finite() or value <= _ZERO:
        raise RiskValidationError(f"{field_name} must be finite and > 0.")


def _require_non_negative(value: Decimal, field_name: str) -> None:
    if not value.is_finite() or value < _ZERO:
        raise RiskValidationError(f"{field_name} must be finite and >= 0.")


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """Explicit limits; production values are intentionally not defaulted."""

    max_risk_per_trade_fraction: Decimal
    max_daily_loss_fraction: Decimal
    max_drawdown_fraction: Decimal
    max_total_exposure_fraction: Decimal
    max_symbol_exposure_fraction: Decimal
    max_abs_correlation: Decimal
    max_open_positions: int
    max_market_data_age_ms: int

    def __post_init__(self) -> None:
        _require_fraction(self.max_risk_per_trade_fraction, "max_risk_per_trade_fraction")
        _require_fraction(self.max_daily_loss_fraction, "max_daily_loss_fraction")
        _require_fraction(self.max_drawdown_fraction, "max_drawdown_fraction")
        _require_fraction(self.max_total_exposure_fraction, "max_total_exposure_fraction")
        _require_fraction(self.max_symbol_exposure_fraction, "max_symbol_exposure_fraction")
        _require_fraction(self.max_abs_correlation, "max_abs_correlation", allow_zero=True)
        if self.max_symbol_exposure_fraction > self.max_total_exposure_fraction:
            raise RiskValidationError(
                "max_symbol_exposure_fraction cannot exceed max_total_exposure_fraction."
            )
        if self.max_open_positions <= 0:
            raise RiskValidationError("max_open_positions must be > 0.")
        if self.max_market_data_age_ms <= 0:
            raise RiskValidationError("max_market_data_age_ms must be > 0.")


@dataclass(frozen=True, slots=True)
class PositionRequest:
    """Requested increase in spot long exposure before risk approval."""

    symbol: str
    requested_notional: Decimal
    risk_at_stop: Decimal
    opens_new_position: bool = True

    def __post_init__(self) -> None:
        if not _SYMBOL_PATTERN.fullmatch(self.symbol):
            raise RiskValidationError(f"Invalid symbol: {self.symbol!r}")
        _require_positive(self.requested_notional, "requested_notional")
        _require_positive(self.risk_at_stop, "risk_at_stop")
        if self.risk_at_stop > self.requested_notional:
            raise RiskValidationError("risk_at_stop cannot exceed requested_notional for spot long.")


@dataclass(frozen=True, slots=True)
class RiskContext:
    """Point-in-time portfolio and system health supplied to the risk gate."""

    equity: Decimal
    start_of_day_equity: Decimal
    peak_equity: Decimal
    gross_exposure: Decimal
    symbol_exposure: Decimal
    open_positions: int
    max_abs_correlation: Decimal
    market_data_age_ms: int
    reconciliation_ok: bool

    def __post_init__(self) -> None:
        _require_positive(self.equity, "equity")
        _require_positive(self.start_of_day_equity, "start_of_day_equity")
        _require_positive(self.peak_equity, "peak_equity")
        _require_non_negative(self.gross_exposure, "gross_exposure")
        _require_non_negative(self.symbol_exposure, "symbol_exposure")
        if self.peak_equity < self.equity:
            raise RiskValidationError("peak_equity cannot be below current equity.")
        if self.symbol_exposure > self.gross_exposure:
            raise RiskValidationError("symbol_exposure cannot exceed gross_exposure.")
        if self.open_positions < 0:
            raise RiskValidationError("open_positions must be >= 0.")
        _require_fraction(self.max_abs_correlation, "max_abs_correlation", allow_zero=True)
        if self.market_data_age_ms < 0:
            raise RiskValidationError("market_data_age_ms must be >= 0.")

    @property
    def daily_loss_fraction(self) -> Decimal:
        loss = self.start_of_day_equity - self.equity
        if loss <= _ZERO:
            return _ZERO
        return loss / self.start_of_day_equity

    @property
    def drawdown_fraction(self) -> Decimal:
        drawdown = self.peak_equity - self.equity
        if drawdown <= _ZERO:
            return _ZERO
        return drawdown / self.peak_equity


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """Auditable result returned before any order can be constructed."""

    decision: RiskDecision
    approved_notional: Decimal
    reasons: tuple[RiskReason, ...]

    def __post_init__(self) -> None:
        _require_non_negative(self.approved_notional, "approved_notional")
        if self.decision is RiskDecision.REJECT and self.approved_notional != _ZERO:
            raise RiskValidationError("Rejected assessments must approve zero notional.")
        if self.decision is RiskDecision.APPROVE and self.reasons:
            raise RiskValidationError("Approved assessments cannot contain limiting reasons.")
        if self.decision is not RiskDecision.APPROVE and not self.reasons:
            raise RiskValidationError("Reduced or rejected assessments require a reason.")
