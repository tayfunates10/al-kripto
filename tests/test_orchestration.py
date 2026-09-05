"""Cross-module tests for the offline/paper validation orchestration layer."""

from __future__ import annotations

import unittest
from collections.abc import Sequence
from dataclasses import replace
from decimal import Decimal

from al_kripto.backtest import BacktestEngine, TargetPosition
from al_kripto.execution import ExecutionStatus, TestExecutionEngine
from al_kripto.market_data import Candle, OrderBookSnapshot, Trade
from al_kripto.ml_research import PredictionRecord
from al_kripto.monitoring import (
    HealthStatus,
    MonitoringSnapshot,
    MonitoringThresholds,
)
from al_kripto.onchain import (
    MetricName,
    MetricObservation,
    OnChainRegimeConfig,
    OnChainRegimeEngine,
    OnChainSnapshot,
)
from al_kripto.orchestration import (
    PaperValidationInputs,
    PaperValidationPipeline,
    PaperValidationPlan,
    PipelineValidationError,
)
from al_kripto.readiness import (
    REQUIRED_READINESS_CHECKS,
    ReadinessEvidence,
    ReadinessStatus,
)
from al_kripto.risk import (
    KillSwitch,
    PositionRequest,
    RiskContext,
    RiskDecision,
    RiskEngine,
    RiskLimits,
)
from al_kripto.smc import SMCEngine, SMCEngineConfig


class _FlatStrategy:
    def target_position(self, history: Sequence[Candle]) -> TargetPosition:
        del history
        return TargetPosition.FLAT


class _FakeMarketData:
    def __init__(self, candles: list[Candle]) -> None:
        self._candles = candles
        self.candle_requests: list[tuple[str, str, int]] = []

    def fetch_candles(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> list[Candle]:
        del start_time_ms, end_time_ms
        self.candle_requests.append((symbol, interval, limit))
        return list(self._candles[:limit])

    def fetch_trades(
        self,
        symbol: str,
        *,
        limit: int = 500,
        start_time_ms: int | None = None,
    ) -> list[Trade]:
        del symbol, limit, start_time_ms
        return []

    def fetch_order_book(self, symbol: str, *, limit: int = 100) -> OrderBookSnapshot:
        del symbol, limit
        raise NotImplementedError


def _candles() -> list[Candle]:
    result: list[Candle] = []
    closes = ("100", "102", "101", "104", "103", "105")
    for index, close_text in enumerate(closes):
        opened = Decimal(close_text) - Decimal("1")
        closed = Decimal(close_text)
        result.append(
            Candle(
                symbol="BTCUSDT",
                interval="1m",
                open_time_ms=index * 60_000,
                close_time_ms=((index + 1) * 60_000) - 1,
                open=opened,
                high=closed + Decimal("2"),
                low=opened - Decimal("2"),
                close=closed,
                volume=Decimal("10"),
                quote_volume=Decimal("1000"),
                trade_count=10,
                taker_buy_base_volume=Decimal("4"),
                taker_buy_quote_volume=Decimal("400"),
            )
        )
    return result


def _risk_limits() -> RiskLimits:
    return RiskLimits(
        max_risk_per_trade_fraction=Decimal("0.02"),
        max_daily_loss_fraction=Decimal("0.05"),
        max_drawdown_fraction=Decimal("0.10"),
        max_total_exposure_fraction=Decimal("0.80"),
        max_symbol_exposure_fraction=Decimal("0.40"),
        max_abs_correlation=Decimal("0.80"),
        max_open_positions=4,
        max_market_data_age_ms=5_000,
    )


def _monitoring_thresholds() -> MonitoringThresholds:
    return MonitoringThresholds(
        max_market_data_age_ms=5_000,
        max_heartbeat_age_ms=10_000,
        warning_drawdown_fraction=Decimal("0.05"),
        critical_drawdown_fraction=Decimal("0.10"),
        warning_daily_loss_fraction=Decimal("0.04"),
        critical_daily_loss_fraction=Decimal("0.08"),
        max_open_orders=3,
    )


def _onchain_snapshot() -> OnChainSnapshot:
    return OnChainSnapshot(
        asset="BTC",
        observations=tuple(
            MetricObservation(
                metric=metric,
                value=Decimal("1.5"),
                percentile=Decimal("0.50"),
                observed_at_ms=1_000,
                available_at_ms=2_000,
            )
            for metric in MetricName
        ),
    )


def _readiness_evidence() -> tuple[ReadinessEvidence, ...]:
    return tuple(
        ReadinessEvidence(
            check=check,
            passed=True,
            reference=f"evidence://{check.value}",
            recorded_at_ms=1_000,
            valid_until_ms=5_000,
        )
        for check in REQUIRED_READINESS_CHECKS
    )


def _inputs() -> PaperValidationInputs:
    return PaperValidationInputs(
        onchain_snapshot=_onchain_snapshot(),
        decision_time_ms=2_500,
        position_request=PositionRequest(
            symbol="BTCUSDT",
            requested_notional=Decimal("100"),
            risk_at_stop=Decimal("10"),
        ),
        risk_context=RiskContext(
            equity=Decimal("1000"),
            start_of_day_equity=Decimal("1000"),
            peak_equity=Decimal("1000"),
            gross_exposure=Decimal("0"),
            symbol_exposure=Decimal("0"),
            open_positions=0,
            max_abs_correlation=Decimal("0.20"),
            market_data_age_ms=100,
            reconciliation_ok=True,
        ),
        monitoring_snapshot=MonitoringSnapshot(
            observed_at_ms=2_500,
            equity=Decimal("1000"),
            start_of_day_equity=Decimal("1000"),
            peak_equity=Decimal("1000"),
            realized_pnl=Decimal("0"),
            market_data_age_ms=100,
            heartbeat_age_ms=100,
            reconciliation_ok=True,
            kill_switch_engaged=False,
            open_orders=0,
        ),
        monitoring_thresholds=_monitoring_thresholds(),
        prediction_records=(
            PredictionRecord(300_000, True, True, Decimal("0.9")),
            PredictionRecord(300_001, False, False, Decimal("0.1")),
        ),
        readiness_evidence=_readiness_evidence(),
        readiness_as_of_ms=2_500,
    )


def _plan() -> PaperValidationPlan:
    return PaperValidationPlan(
        symbol="BTCUSDT",
        base_asset="BTC",
        interval="1m",
        candle_limit=6,
        ml_train_size=2,
        ml_validation_size=1,
        ml_test_size=1,
        ml_purge_size=1,
        client_order_id="paper-cycle-1",
        quantity_step=Decimal("0.001"),
    )


def _pipeline(source: _FakeMarketData) -> PaperValidationPipeline:
    return PaperValidationPipeline(
        market_data=source,
        backtest=BacktestEngine(clock_ms=lambda: 1_000_000),
        strategy=_FlatStrategy(),
        smc=SMCEngine(SMCEngineConfig(swing_strength=1)),
        onchain=OnChainRegimeEngine(
            OnChainRegimeConfig(
                minimum_metrics=3,
                consensus_metrics=3,
                max_age_ms=10_000,
                max_observation_age_ms=10_000,
            )
        ),
        risk=RiskEngine(_risk_limits(), KillSwitch(engaged=False)),
        execution=TestExecutionEngine(),
    )


class PaperValidationPipelineTests(unittest.TestCase):
    def test_full_cycle_wires_all_modules_without_live_trading(self) -> None:
        source = _FakeMarketData(_candles())
        cycle = _pipeline(source).run(_plan(), _inputs())

        self.assertEqual(source.candle_requests, [("BTCUSDT", "1m", 6)])
        self.assertEqual(len(cycle.candles), 6)
        self.assertEqual(cycle.backtest.fills, ())
        self.assertEqual(cycle.risk.decision, RiskDecision.APPROVE)
        self.assertEqual(cycle.monitoring.status, HealthStatus.HEALTHY)
        self.assertEqual(cycle.ml_split.test[-1], cycle.candles[-1])
        self.assertEqual(dict(cycle.ml_metrics)["accuracy"], Decimal("1"))
        self.assertEqual(cycle.readiness.status, ReadinessStatus.READY_FOR_MANUAL_REVIEW)
        self.assertIsNotNone(cycle.test_order)
        assert cycle.test_order is not None
        self.assertEqual(cycle.test_order.status, ExecutionStatus.NEW)
        self.assertEqual(cycle.test_order.symbol, "BTCUSDT")
        self.assertFalse(cycle.live_trading_enabled)

    def test_pipeline_can_run_same_plan_across_distinct_decision_times(self) -> None:
        source = _FakeMarketData(_candles())
        pipeline = _pipeline(source)
        first_inputs = _inputs()
        second_inputs = replace(
            first_inputs,
            decision_time_ms=2_501,
            monitoring_snapshot=replace(first_inputs.monitoring_snapshot, observed_at_ms=2_501),
            position_request=replace(
                first_inputs.position_request,
                requested_notional=Decimal("50"),
                risk_at_stop=Decimal("5"),
            ),
        )

        first = pipeline.run(_plan(), first_inputs)
        second = pipeline.run(_plan(), second_inputs)

        assert first.test_order is not None
        assert second.test_order is not None
        self.assertEqual(first.test_order.client_order_id, "paper-cycle-1-2500")
        self.assertEqual(second.test_order.client_order_id, "paper-cycle-1-2501")
        self.assertNotEqual(first.test_order.client_order_id, second.test_order.client_order_id)
        self.assertNotEqual(first.test_order.quantity, second.test_order.quantity)
        self.assertFalse(first.live_trading_enabled)
        self.assertFalse(second.live_trading_enabled)

    def test_execution_collision_is_wrapped_as_pipeline_validation_error(self) -> None:
        source = _FakeMarketData(_candles())
        pipeline = _pipeline(source)
        first_inputs = _inputs()
        pipeline.run(_plan(), first_inputs)
        conflicting = replace(
            first_inputs,
            position_request=replace(
                first_inputs.position_request,
                requested_notional=Decimal("50"),
                risk_at_stop=Decimal("5"),
            ),
        )

        with self.assertRaises(PipelineValidationError):
            pipeline.run(_plan(), conflicting)

    def test_paused_monitoring_prevents_even_test_order_submission(self) -> None:
        source = _FakeMarketData(_candles())
        inputs = _inputs()
        paused = replace(
            inputs,
            monitoring_snapshot=replace(
                inputs.monitoring_snapshot,
                kill_switch_engaged=True,
            ),
        )

        cycle = _pipeline(source).run(_plan(), paused)

        self.assertEqual(cycle.monitoring.status, HealthStatus.PAUSED)
        self.assertIsNone(cycle.test_order)
        self.assertFalse(cycle.live_trading_enabled)

    def test_inconsistent_risk_and_monitoring_equity_is_rejected(self) -> None:
        inputs = _inputs()

        with self.assertRaises(PipelineValidationError):
            replace(
                inputs,
                monitoring_snapshot=replace(
                    inputs.monitoring_snapshot,
                    equity=Decimal("999"),
                ),
            )

    def test_test_order_quantity_is_rounded_to_the_plan_quantity_step(self) -> None:
        source = _FakeMarketData(_candles())

        cycle = _pipeline(source).run(_plan(), _inputs())

        assert cycle.test_order is not None
        step = _plan().quantity_step
        self.assertEqual(cycle.test_order.quantity % step, Decimal("0"))
        self.assertGreater(cycle.test_order.quantity, Decimal("0"))

    def test_notional_below_one_quantity_step_is_rejected(self) -> None:
        source = _FakeMarketData(_candles())
        coarse = replace(_plan(), quantity_step=Decimal("1000"))

        with self.assertRaises(PipelineValidationError):
            _pipeline(source).run(coarse, _inputs())

    def test_onchain_asset_prefix_does_not_pass_as_base_asset(self) -> None:
        source = _FakeMarketData(_candles())
        inputs = _inputs()
        prefixed = replace(
            inputs,
            onchain_snapshot=OnChainSnapshot(
                asset="BT",
                observations=tuple(
                    observation
                    for observation in inputs.onchain_snapshot.observations
                    if observation.metric is not MetricName.PUELL_MULTIPLE
                ),
            ),
        )

        with self.assertRaises(PipelineValidationError):
            _pipeline(source).run(_plan(), prefixed)

    def test_short_market_data_response_raises_pipeline_error(self) -> None:
        source = _FakeMarketData(_candles()[:4])

        with self.assertRaises(PipelineValidationError):
            _pipeline(source).run(_plan(), _inputs())

    def test_predictions_outside_the_test_window_are_rejected(self) -> None:
        source = _FakeMarketData(_candles())
        inputs = _inputs()
        drifted = replace(
            inputs,
            prediction_records=(PredictionRecord(999_999_999, True, True, Decimal("0.9")),),
        )

        with self.assertRaises(PipelineValidationError):
            _pipeline(source).run(_plan(), drifted)


if __name__ == "__main__":
    unittest.main()
