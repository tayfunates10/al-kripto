"""Read-only monitoring evaluation and dashboard payload rendering."""

from __future__ import annotations

from .models import (
    AlertCode,
    AlertSeverity,
    HealthStatus,
    MonitoringAlert,
    MonitoringReport,
    MonitoringSnapshot,
    MonitoringThresholds,
)


def evaluate_monitoring(
    snapshot: MonitoringSnapshot,
    thresholds: MonitoringThresholds,
) -> MonitoringReport:
    """Evaluate portfolio/system telemetry without mutating trading state."""
    alerts: list[MonitoringAlert] = []

    if snapshot.kill_switch_engaged:
        alerts.append(
            MonitoringAlert(
                AlertCode.KILL_SWITCH,
                AlertSeverity.CRITICAL,
                "Kill-switch is engaged; exposure increases should remain blocked.",
            )
        )
    if not snapshot.reconciliation_ok:
        alerts.append(
            MonitoringAlert(
                AlertCode.RECONCILIATION_ERROR,
                AlertSeverity.CRITICAL,
                "Local and external state reconciliation is not healthy.",
            )
        )
    if snapshot.market_data_age_ms > thresholds.max_market_data_age_ms:
        alerts.append(
            MonitoringAlert(
                AlertCode.STALE_MARKET_DATA,
                AlertSeverity.CRITICAL,
                "Market data is older than the configured monitoring threshold.",
            )
        )
    if snapshot.heartbeat_age_ms > thresholds.max_heartbeat_age_ms:
        alerts.append(
            MonitoringAlert(
                AlertCode.STALE_HEARTBEAT,
                AlertSeverity.CRITICAL,
                "System heartbeat is older than the configured monitoring threshold.",
            )
        )
    if snapshot.unhandled_errors > 0:
        alerts.append(
            MonitoringAlert(
                AlertCode.SYSTEM_ERRORS,
                AlertSeverity.CRITICAL,
                f"Observed {snapshot.unhandled_errors} unhandled system error(s).",
            )
        )

    drawdown = snapshot.drawdown_fraction
    if drawdown >= thresholds.critical_drawdown_fraction:
        alerts.append(
            MonitoringAlert(
                AlertCode.DRAWDOWN_LIMIT,
                AlertSeverity.CRITICAL,
                "Drawdown reached or exceeded the configured critical threshold.",
            )
        )
    elif drawdown >= thresholds.warning_drawdown_fraction:
        alerts.append(
            MonitoringAlert(
                AlertCode.DRAWDOWN_WARNING,
                AlertSeverity.WARNING,
                "Drawdown reached or exceeded the configured warning threshold.",
            )
        )

    daily_loss = snapshot.daily_loss_fraction
    if daily_loss >= thresholds.critical_daily_loss_fraction:
        alerts.append(
            MonitoringAlert(
                AlertCode.DAILY_LOSS_LIMIT,
                AlertSeverity.CRITICAL,
                "Daily loss reached or exceeded the configured critical threshold.",
            )
        )
    elif daily_loss >= thresholds.warning_daily_loss_fraction:
        alerts.append(
            MonitoringAlert(
                AlertCode.DAILY_LOSS_WARNING,
                AlertSeverity.WARNING,
                "Daily loss reached or exceeded the configured warning threshold.",
            )
        )

    if snapshot.open_orders > thresholds.max_open_orders:
        alerts.append(
            MonitoringAlert(
                AlertCode.OPEN_ORDERS_WARNING,
                AlertSeverity.WARNING,
                "Open order count exceeds the configured monitoring threshold.",
            )
        )

    if any(alert.severity is AlertSeverity.CRITICAL for alert in alerts):
        status = HealthStatus.BLOCKED
    elif alerts:
        status = HealthStatus.DEGRADED
    else:
        status = HealthStatus.HEALTHY

    return MonitoringReport(status=status, snapshot=snapshot, alerts=tuple(alerts))


def dashboard_payload(report: MonitoringReport) -> dict[str, object]:
    """Return a JSON-safe read-only dashboard representation without credentials."""
    snapshot = report.snapshot
    return {
        "status": report.status.value,
        "observed_at_ms": snapshot.observed_at_ms,
        "equity": str(snapshot.equity),
        "daily_pnl": str(snapshot.daily_pnl),
        "realized_pnl": str(snapshot.realized_pnl),
        "drawdown_fraction": str(snapshot.drawdown_fraction),
        "daily_loss_fraction": str(snapshot.daily_loss_fraction),
        "market_data_age_ms": snapshot.market_data_age_ms,
        "heartbeat_age_ms": snapshot.heartbeat_age_ms,
        "reconciliation_ok": snapshot.reconciliation_ok,
        "kill_switch_engaged": snapshot.kill_switch_engaged,
        "open_orders": snapshot.open_orders,
        "unhandled_errors": snapshot.unhandled_errors,
        "alerts": [
            {
                "code": alert.code.value,
                "severity": alert.severity.value,
                "message": alert.message,
            }
            for alert in report.alerts
        ],
    }
