"""Tests for read-only monitoring and dashboard payloads."""

from __future__ import annotations

import unittest
from decimal import Decimal

from al_kripto.monitoring import (
    AlertCode,
    HealthStatus,
    MonitoringSnapshot,
    MonitoringThresholds,
    MonitoringValidationError,
    dashboard_payload,
    evaluate_monitoring,
)


def _thresholds() -> MonitoringThresholds:
    return MonitoringThresholds(
        max_market_data_age_ms=5_000,
        max_heartbeat_age_ms=10_000,
        warning_drawdown_fraction=Decimal("0.05"),
        critical_drawdown_fraction=Decimal("0.10"),
        warning_daily_loss_fraction=Decimal("0.04"),
        critical_daily_loss_fraction=Decimal("0.08"),
        max_open_orders=3,
    )


def _snapshot(**overrides: object) -> MonitoringSnapshot:
    values: dict[str, object] = {
        "observed_at_ms": 100_000,
        "equity": Decimal("1000"),
        "start_of_day_equity": Decimal("1000"),
        "peak_equity": Decimal("1000"),
        "realized_pnl": Decimal("0"),
        "market_data_age_ms": 100,
        "heartbeat_age_ms": 100,
        "reconciliation_ok": True,
        "kill_switch_engaged": False,
        "open_orders": 1,
        "unhandled_errors": 0,
    }
    values.update(overrides)
    return MonitoringSnapshot(**values)  # type: ignore[arg-type]


class MonitoringEvaluationTests(unittest.TestCase):
    def test_healthy_snapshot_has_no_alerts(self) -> None:
        report = evaluate_monitoring(_snapshot(), _thresholds())

        self.assertEqual(report.status, HealthStatus.HEALTHY)
        self.assertEqual(report.alerts, ())

    def test_stale_market_data_blocks_health(self) -> None:
        report = evaluate_monitoring(
            _snapshot(market_data_age_ms=5_001),
            _thresholds(),
        )

        self.assertEqual(report.status, HealthStatus.BLOCKED)
        self.assertIn(AlertCode.STALE_MARKET_DATA, tuple(alert.code for alert in report.alerts))

    def test_reconciliation_and_kill_switch_are_critical(self) -> None:
        report = evaluate_monitoring(
            _snapshot(reconciliation_ok=False, kill_switch_engaged=True),
            _thresholds(),
        )

        codes = tuple(alert.code for alert in report.alerts)
        self.assertEqual(report.status, HealthStatus.BLOCKED)
        self.assertIn(AlertCode.RECONCILIATION_ERROR, codes)
        self.assertIn(AlertCode.KILL_SWITCH, codes)

    def test_warning_drawdown_degrades_without_blocking(self) -> None:
        report = evaluate_monitoring(
            _snapshot(
                equity=Decimal("950"),
                start_of_day_equity=Decimal("1000"),
                peak_equity=Decimal("1000"),
            ),
            _thresholds(),
        )

        codes = tuple(alert.code for alert in report.alerts)
        self.assertEqual(report.status, HealthStatus.DEGRADED)
        self.assertIn(AlertCode.DRAWDOWN_WARNING, codes)
        self.assertIn(AlertCode.DAILY_LOSS_WARNING, codes)

    def test_critical_loss_and_drawdown_block_health(self) -> None:
        report = evaluate_monitoring(
            _snapshot(
                equity=Decimal("800"),
                start_of_day_equity=Decimal("1000"),
                peak_equity=Decimal("1000"),
            ),
            _thresholds(),
        )

        codes = tuple(alert.code for alert in report.alerts)
        self.assertEqual(report.status, HealthStatus.BLOCKED)
        self.assertIn(AlertCode.DRAWDOWN_LIMIT, codes)
        self.assertIn(AlertCode.DAILY_LOSS_LIMIT, codes)
        self.assertNotIn(AlertCode.DRAWDOWN_WARNING, codes)
        self.assertNotIn(AlertCode.DAILY_LOSS_WARNING, codes)

    def test_stale_heartbeat_and_system_errors_block_health(self) -> None:
        report = evaluate_monitoring(
            _snapshot(heartbeat_age_ms=10_001, unhandled_errors=2),
            _thresholds(),
        )

        codes = tuple(alert.code for alert in report.alerts)
        self.assertEqual(report.status, HealthStatus.BLOCKED)
        self.assertIn(AlertCode.STALE_HEARTBEAT, codes)
        self.assertIn(AlertCode.SYSTEM_ERRORS, codes)

    def test_open_order_excess_is_warning_only(self) -> None:
        report = evaluate_monitoring(_snapshot(open_orders=4), _thresholds())

        self.assertEqual(report.status, HealthStatus.DEGRADED)
        self.assertEqual(
            tuple(alert.code for alert in report.alerts),
            (AlertCode.OPEN_ORDERS_WARNING,),
        )

    def test_dashboard_payload_is_json_safe_and_read_only(self) -> None:
        report = evaluate_monitoring(
            _snapshot(realized_pnl=Decimal("12.5"), open_orders=4),
            _thresholds(),
        )

        payload = dashboard_payload(report)

        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["equity"], "1000")
        self.assertEqual(payload["daily_pnl"], "0")
        self.assertEqual(payload["realized_pnl"], "12.5")
        self.assertNotIn("api_key", payload)
        self.assertNotIn("api_secret", payload)


class MonitoringValidationTests(unittest.TestCase):
    def test_rejects_inverted_drawdown_thresholds(self) -> None:
        with self.assertRaises(MonitoringValidationError):
            MonitoringThresholds(
                max_market_data_age_ms=1,
                max_heartbeat_age_ms=1,
                warning_drawdown_fraction=Decimal("0.2"),
                critical_drawdown_fraction=Decimal("0.1"),
                warning_daily_loss_fraction=Decimal("0.1"),
                critical_daily_loss_fraction=Decimal("0.2"),
                max_open_orders=0,
            )

    def test_rejects_peak_equity_below_current_equity(self) -> None:
        with self.assertRaises(MonitoringValidationError):
            _snapshot(equity=Decimal("1001"), peak_equity=Decimal("1000"))


if __name__ == "__main__":
    unittest.main()
