"""Deterministic offline/paper cycle wiring research and safety modules together."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from al_kripto.backtest import BacktestEngine, BacktestResult, BacktestStrategy
from al_kripto.execution import ExecutionOrder, TestExecutionEngine
from al_kripto.execution import Side as ExecutionSide
from al_kripto.market_data import Candle, MarketDataSource
from al_kripto.ml_research import (
    ChronologicalSplit,
    PredictionRecord,
    binary_classification_metrics,
    chronological_split,
)
from al_kripto.monitoring import (
    HealthStatus,
    MonitoringReport,
    MonitoringSnapshot,
    MonitoringThresholds,
    evaluate_monitoring,
)
from al_kripto.onchain import OnChainRegimeAssessment, OnChainRegimeEngine, OnChainSnapshot
from al_kripto.readiness import (
    ReadinessAssessment,
    ReadinessEvidence,
    assess_production_readiness,
)
from al_kripto.risk import PositionRequest, RiskAssessment, RiskContext, RiskDecision, RiskEngine
from al_kripto.smc import SMCAnalysis, SMCEngine

_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")


class PipelineValidationError(ValueError):
    """Raised when one paper-cycle input contradicts another input."""


@dataclass(frozen=True, slots=True)
class PaperValidationPlan:
    """Static plan for one offline/paper validation cycle."""

    symbol: str
    interval: str
    candle_limit: int
    ml_train_size: int
    ml_validation_size: int
    ml_test_size: int
    ml_purge_size: int
    client_order_id: str

    def __post_init__(self) -> None:
        if not _SYMBOL_PATTERN.fullmatch(self.symbol):
            raise PipelineValidationError(f"invalid symbol: {self.symbol!r}")
        if not self.interval.strip():
            raise PipelineValidationError("interval must not be empty.")
        if self.candle_limit <= 0:
            raise PipelineValidationError("candle_limit must be > 0.")
        sizes = (self.ml_train_size, self.ml_validation_size, self.ml_test_size)
        if any(size <= 0 for size in sizes):
            raise PipelineValidationError("ML split sizes must be > 0.")
        if self.ml_purge_size < 0:
            raise PipelineValidationError("ml_purge_size must be >= 0.")
        required = sum(sizes) + (2 * self.ml_purge_size)
        if self.candle_limit < required:
            raise PipelineValidationError(
                "candle_limit must cover train, validation, test and purge samples."
            )
        if not self.client_order_id.strip():
            raise PipelineValidationError("client_order_id must not be empty.")


@dataclass(frozen=True, slots=True)
class PaperValidationInputs:
    """Point-in-time safety/research inputs that are not fetched from private APIs."""

    onchain_snapshot: OnChainSnapshot
    decision_time_ms: int
    position_request: PositionRequest
    risk_context: RiskContext
    monitoring_snapshot: MonitoringSnapshot
    monitoring_thresholds: MonitoringThresholds
    prediction_records: tuple[PredictionRecord, ...]
    readiness_evidence: tuple[ReadinessEvidence, ...]
    readiness_as_of_ms: int

    def __post_init__(self) -> None:
        if self.decision_time_ms < 0 or self.readiness_as_of_ms < 0:
            raise PipelineValidationError("cycle decision times must be >= 0.")
        if self.risk_context.equity != self.monitoring_snapshot.equity:
            raise PipelineValidationError(
                "risk and monitoring equity must describe the same point-in-time state."
            )


@dataclass(frozen=True, slots=True)
class PaperValidationCycle:
    """Immutable result of one cross-module paper validation cycle."""

    candles: tuple[Candle, ...]
    backtest: BacktestResult
    smc: SMCAnalysis
    onchain: OnChainRegimeAssessment
    risk: RiskAssessment
    monitoring: MonitoringReport
    ml_split: ChronologicalSplit[Candle]
    ml_metrics: tuple[tuple[str, Decimal], ...]
    readiness: ReadinessAssessment
    test_order: ExecutionOrder | None
    live_trading_enabled: bool = field(default=False, init=False)


class PaperValidationPipeline:
    """Wire modules together without credentials, live endpoints, or real-money orders."""

    def __init__(
        self,
        *,
        market_data: MarketDataSource,
        backtest: BacktestEngine,
        strategy: BacktestStrategy,
        smc: SMCEngine,
        onchain: OnChainRegimeEngine,
        risk: RiskEngine,
        execution: TestExecutionEngine,
    ) -> None:
        self._market_data = market_data
        self._backtest = backtest
        self._strategy = strategy
        self._smc = smc
        self._onchain = onchain
        self._risk = risk
        self._execution = execution

    def run(
        self,
        plan: PaperValidationPlan,
        inputs: PaperValidationInputs,
    ) -> PaperValidationCycle:
        """Run a full offline/paper cycle; the only order object is in-memory test execution."""
        if inputs.position_request.symbol != plan.symbol:
            raise PipelineValidationError("position request symbol must match the cycle symbol.")
        if not plan.symbol.startswith(inputs.onchain_snapshot.asset):
            raise PipelineValidationError("on-chain asset must match the cycle symbol.")

        candles = tuple(
            self._market_data.fetch_candles(
                plan.symbol,
                plan.interval,
                limit=plan.candle_limit,
            )
        )
        backtest_result = self._backtest.run(candles, self._strategy)
        smc_result = self._smc.analyze(candles)
        onchain_result = self._onchain.classify(
            inputs.onchain_snapshot,
            decision_time_ms=inputs.decision_time_ms,
        )
        risk_result = self._risk.evaluate(inputs.position_request, inputs.risk_context)
        monitoring_result = evaluate_monitoring(
            inputs.monitoring_snapshot,
            inputs.monitoring_thresholds,
        )
        ml_split = chronological_split(
            candles,
            train_size=plan.ml_train_size,
            validation_size=plan.ml_validation_size,
            test_size=plan.ml_test_size,
            purge_size=plan.ml_purge_size,
        )
        ml_metrics = tuple(binary_classification_metrics(inputs.prediction_records).items())
        readiness = assess_production_readiness(
            inputs.readiness_evidence,
            as_of_ms=inputs.readiness_as_of_ms,
        )

        test_order: ExecutionOrder | None = None
        if (
            risk_result.decision is not RiskDecision.REJECT
            and monitoring_result.status is HealthStatus.HEALTHY
        ):
            latest_price = candles[-1].close
            quantity = risk_result.approved_notional / latest_price
            test_order = self._execution.submit(
                client_order_id=plan.client_order_id,
                symbol=plan.symbol,
                side=ExecutionSide.BUY,
                quantity=quantity,
            )

        return PaperValidationCycle(
            candles=candles,
            backtest=backtest_result,
            smc=smc_result,
            onchain=onchain_result,
            risk=risk_result,
            monitoring=monitoring_result,
            ml_split=ml_split,
            ml_metrics=ml_metrics,
            readiness=readiness,
            test_order=test_order,
        )
