"""Validated read-only monitoring models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

_ZERO = Decimal("0")
_ONE = Decimal("1")


class MonitoringValidationError(ValueError):
    """Raised when a monitoring snapshot or threshold set is inconsistent."""


class HealthStatus(StrEnum):
    """Overall read-only health state."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class AlertSeverity(StrEnum):
    """Monitoring alert severity."""

    WARNING = "warning"
    CRITICAL = "critical"


class AlertCode(StrEnum):
    """Stable alert identifiers for dashboards and automation."""

    STALE_MARKET_DATA = "stale_market_data"
    STALE_HEARTBEAT = "stale_heartbeat"
    RECONCILIATION_ERROR = "reconciliation_error"
    KILL_SWITCH = "kill_switch"
    ACCOUNT_DEPLETED = "account_depleted"
    INCONSISTENT_EQUITY_STATE = "inconsistent_equity_state"
    DRAWDOWN_WARNING = "drawdown_warning"
    DRAWDOWN_LIMIT = "drawdown_limit"
    DAILY_LOSS_WARNING = "daily_loss_warning"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    OPEN_ORDERS_WARNING = "open_orders_warning"
    SYSTEM_ERRORS = "system_errors"


def _require_positive_fraction(value: Decimal, field_name: str) -> None:
    if not value.is_finite() or not _ZERO < value <= _ONE:
        raise MonitoringValidationError(f"{field_name} must be finite and in (0, 1].")


def _require_positive(value: Decimal, field_name: str) -> None:
    if not value.is_finite() or value <= _ZERO:
        raise MonitoringValidationError(f"{field_name} must be finite and > 0.")


def _require_non_negative(value: Decimal, field_name: str) -> None:
    if not value.is_finite() or value < _ZERO:
        raise MonitoringValidationError(f"{field_name} must be finite and >= 0.")


@dataclass(frozen=True, slots=True)
class MonitoringThresholds:
    """Explicit alarm thresholds; no production investment values are defaulted."""

    max_market_data_age_ms: int
    max_heartbeat_age_ms: int
    warning_drawdown_fraction: Decimal
    critical_drawdown_fraction: Decimal
    warning_daily_loss_fraction: Decimal
    critical_daily_loss_fraction: Decimal
    max_open_orders: int

    def __post_init__(self) -> None:
        if self.max_market_data_age_ms <= 0:
            raise MonitoringValidationError("max_market_data_age_ms must be > 0.")
        if self.max_heartbeat_age_ms <= 0:
            raise MonitoringValidationError("max_heartbeat_age_ms must be > 0.")
        if self.max_open_orders < 0:
            raise MonitoringValidationError("max_open_orders must be >= 0.")

        _require_positive_fraction(self.warning_drawdown_fraction, "warning_drawdown_fraction")
        _require_positive_fraction(self.critical_drawdown_fraction, "critical_drawdown_fraction")
        _require_positive_fraction(
            self.warning_daily_loss_fraction,
            "warning_daily_loss_fraction",
        )
        _require_positive_fraction(
            self.critical_daily_loss_fraction,
            "critical_daily_loss_fraction",
        )

        if self.warning_drawdown_fraction >= self.critical_drawdown_fraction:
            raise MonitoringValidationError(
                "warning_drawdown_fraction must be below critical_drawdown_fraction."
            )
        if self.warning_daily_loss_fraction >= self.critical_daily_loss_fraction:
            raise MonitoringValidationError(
                "warning_daily_loss_fraction must be below critical_daily_loss_fraction."
            )


@dataclass(frozen=True, slots=True)
class MonitoringSnapshot:
    """Point-in-time portfolio and system telemetry without credentials or order access."""

    observed_at_ms: int
    equity: Decimal
    start_of_day_equity: Decimal
    peak_equity: Decimal
    realized_pnl: Decimal
    market_data_age_ms: int
    heartbeat_age_ms: int
    reconciliation_ok: bool
    kill_switch_engaged: bool
    open_orders: int
    unhandled_errors: int = 0

    def __post_init__(self) -> None:
        if self.observed_at_ms < 0:
            raise MonitoringValidationError("observed_at_ms must be >= 0.")
        _require_non_negative(self.equity, "equity")
        _require_positive(self.start_of_day_equity, "start_of_day_equity")
        _require_non_negative(self.peak_equity, "peak_equity")
        if not self.realized_pnl.is_finite():
            raise MonitoringValidationError("realized_pnl must be finite.")
        if self.market_data_age_ms < 0:
            raise MonitoringValidationError("market_data_age_ms must be >= 0.")
        if self.heartbeat_age_ms < 0:
            raise MonitoringValidationError("heartbeat_age_ms must be >= 0.")
        if self.open_orders < 0:
            raise MonitoringValidationError("open_orders must be >= 0.")
        if self.unhandled_errors < 0:
            raise MonitoringValidationError("unhandled_errors must be >= 0.")

    @property
    def daily_pnl(self) -> Decimal:
        """Mark-to-market daily PnL derived from equity."""
        return self.equity - self.start_of_day_equity

    @property
    def daily_loss_fraction(self) -> Decimal:
        """Non-negative daily loss fraction."""
        loss = self.start_of_day_equity - self.equity
        if loss <= _ZERO:
            return _ZERO
        return loss / self.start_of_day_equity

    @property
    def drawdown_fraction(self) -> Decimal:
        """Non-negative drawdown from the reported peak equity."""
        if self.peak_equity <= _ZERO or self.peak_equity < self.equity:
            return _ZERO
        drawdown = self.peak_equity - self.equity
        if drawdown <= _ZERO:
            return _ZERO
        return drawdown / self.peak_equity


@dataclass(frozen=True, slots=True)
class MonitoringAlert:
    """One immutable monitoring finding."""

    code: AlertCode
    severity: AlertSeverity
    message: str

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise MonitoringValidationError("alert message must not be empty.")


@dataclass(frozen=True, slots=True)
class MonitoringReport:
    """Read-only health report rendered by the monitoring engine."""

    status: HealthStatus
    snapshot: MonitoringSnapshot
    alerts: tuple[MonitoringAlert, ...]

    def __post_init__(self) -> None:
        has_critical = any(alert.severity is AlertSeverity.CRITICAL for alert in self.alerts)
        if self.status is HealthStatus.BLOCKED and not has_critical:
            raise MonitoringValidationError("blocked reports require a critical alert.")
        if self.status is HealthStatus.HEALTHY and self.alerts:
            raise MonitoringValidationError("healthy reports cannot contain alerts.")
