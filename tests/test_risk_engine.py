"""Tests for the fail-closed central risk gate."""

from __future__ import annotations

import unittest
from decimal import Decimal

from al_kripto.risk import (
    KillSwitch,
    PositionRequest,
    RiskContext,
    RiskDecision,
    RiskEngine,
    RiskLimits,
    RiskReason,
    RiskValidationError,
)


def limits() -> RiskLimits:
    """Test-only values; these are not production recommendations."""
    return RiskLimits(
        max_risk_per_trade_fraction=Decimal("0.01"),
        max_daily_loss_fraction=Decimal("0.05"),
        max_drawdown_fraction=Decimal("0.10"),
        max_total_exposure_fraction=Decimal("0.80"),
        max_symbol_exposure_fraction=Decimal("0.40"),
        max_abs_correlation=Decimal("0.80"),
        max_open_positions=4,
        max_market_data_age_ms=5_000,
    )


def context(**overrides: object) -> RiskContext:
    values: dict[str, object] = {
        "equity": Decimal("10000"),
        "start_of_day_equity": Decimal("10000"),
        "peak_equity": Decimal("10000"),
        "gross_exposure": Decimal("1000"),
        "symbol_exposure": Decimal("500"),
        "open_positions": 1,
        "max_abs_correlation": Decimal("0.20"),
        "market_data_age_ms": 500,
        "reconciliation_ok": True,
    }
    values.update(overrides)
    return RiskContext(**values)  # type: ignore[arg-type]


def request(**overrides: object) -> PositionRequest:
    values: dict[str, object] = {
        "symbol": "BTCUSDT",
        "requested_notional": Decimal("1000"),
        "risk_at_stop": Decimal("100"),
        "opens_new_position": True,
    }
    values.update(overrides)
    return PositionRequest(**values)  # type: ignore[arg-type]


class RiskEngineBlockingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.kill_switch = KillSwitch(engaged=False)
        self.engine = RiskEngine(limits(), self.kill_switch)

    def assert_rejected(self, assessment_reason: RiskReason, portfolio: RiskContext) -> None:
        result = self.engine.evaluate(request(), portfolio)
        self.assertEqual(result.decision, RiskDecision.REJECT)
        self.assertEqual(result.approved_notional, Decimal("0"))
        self.assertEqual(result.reasons, (assessment_reason,))

    def test_kill_switch_blocks_exposure_immediately(self) -> None:
        self.kill_switch.engage()
        self.assert_rejected(RiskReason.KILL_SWITCH, context())

    def test_reconciliation_error_fails_closed(self) -> None:
        self.assert_rejected(
            RiskReason.RECONCILIATION_ERROR,
            context(reconciliation_ok=False),
        )

    def test_stale_market_data_fails_closed(self) -> None:
        self.assert_rejected(
            RiskReason.STALE_MARKET_DATA,
            context(market_data_age_ms=5_001),
        )

    def test_daily_loss_limit_blocks_new_risk(self) -> None:
        self.assert_rejected(
            RiskReason.DAILY_LOSS_LIMIT,
            context(equity=Decimal("9500"), peak_equity=Decimal("10000")),
        )

    def test_drawdown_limit_blocks_new_risk(self) -> None:
        self.assert_rejected(
            RiskReason.DRAWDOWN_LIMIT,
            context(
                equity=Decimal("9000"),
                start_of_day_equity=Decimal("9000"),
                peak_equity=Decimal("10000"),
            ),
        )

    def test_open_position_limit_blocks_new_position(self) -> None:
        self.assert_rejected(RiskReason.MAX_OPEN_POSITIONS, context(open_positions=4))

    def test_correlation_limit_blocks_concentrated_exposure(self) -> None:
        self.assert_rejected(
            RiskReason.CORRELATION_LIMIT,
            context(max_abs_correlation=Decimal("0.80")),
        )


class RiskEngineSizingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RiskEngine(limits(), KillSwitch(engaged=False))

    def test_safe_request_is_approved_unchanged(self) -> None:
        result = self.engine.evaluate(request(), context())
        self.assertEqual(result.decision, RiskDecision.APPROVE)
        self.assertEqual(result.approved_notional, Decimal("1000"))
        self.assertEqual(result.reasons, ())

    def test_trade_risk_limit_only_reduces_size(self) -> None:
        result = self.engine.evaluate(
            request(requested_notional=Decimal("2000"), risk_at_stop=Decimal("400")),
            context(),
        )
        self.assertEqual(result.decision, RiskDecision.REDUCE)
        self.assertEqual(result.approved_notional, Decimal("500"))
        self.assertIn(RiskReason.TRADE_RISK_LIMIT, result.reasons)

    def test_total_exposure_limit_reduces_size(self) -> None:
        result = self.engine.evaluate(
            request(requested_notional=Decimal("1000"), risk_at_stop=Decimal("50")),
            context(gross_exposure=Decimal("7500"), symbol_exposure=Decimal("500")),
        )
        self.assertEqual(result.decision, RiskDecision.REDUCE)
        self.assertEqual(result.approved_notional, Decimal("500"))
        self.assertIn(RiskReason.TOTAL_EXPOSURE_LIMIT, result.reasons)

    def test_symbol_exposure_limit_reduces_size(self) -> None:
        result = self.engine.evaluate(
            request(requested_notional=Decimal("1000"), risk_at_stop=Decimal("50")),
            context(gross_exposure=Decimal("5000"), symbol_exposure=Decimal("3500")),
        )
        self.assertEqual(result.decision, RiskDecision.REDUCE)
        self.assertEqual(result.approved_notional, Decimal("500"))
        self.assertIn(RiskReason.SYMBOL_EXPOSURE_LIMIT, result.reasons)

    def test_zero_remaining_exposure_rejects(self) -> None:
        result = self.engine.evaluate(
            request(risk_at_stop=Decimal("50")),
            context(gross_exposure=Decimal("8000"), symbol_exposure=Decimal("4000")),
        )
        self.assertEqual(result.decision, RiskDecision.REJECT)
        self.assertEqual(result.approved_notional, Decimal("0"))

    def test_risk_budget_shrinks_with_equity_after_loss(self) -> None:
        healthy = self.engine.evaluate(
            request(requested_notional=Decimal("2000"), risk_at_stop=Decimal("200")),
            context(),
        )
        reduced_equity = self.engine.evaluate(
            request(requested_notional=Decimal("2000"), risk_at_stop=Decimal("200")),
            context(
                equity=Decimal("9800"),
                start_of_day_equity=Decimal("10000"),
                peak_equity=Decimal("10000"),
            ),
        )
        self.assertLess(reduced_equity.approved_notional, healthy.approved_notional)


class RiskValidationTests(unittest.TestCase):
    def test_limits_require_explicit_valid_fractions(self) -> None:
        with self.assertRaises(RiskValidationError):
            RiskLimits(
                max_risk_per_trade_fraction=Decimal("0"),
                max_daily_loss_fraction=Decimal("0.05"),
                max_drawdown_fraction=Decimal("0.10"),
                max_total_exposure_fraction=Decimal("0.80"),
                max_symbol_exposure_fraction=Decimal("0.40"),
                max_abs_correlation=Decimal("0.80"),
                max_open_positions=4,
                max_market_data_age_ms=5_000,
            )

    def test_spot_risk_at_stop_cannot_exceed_notional(self) -> None:
        with self.assertRaises(RiskValidationError):
            request(requested_notional=Decimal("100"), risk_at_stop=Decimal("101"))


if __name__ == "__main__":
    unittest.main()
