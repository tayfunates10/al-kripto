"""Fail-closed central risk gate for exposure-increasing requests."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import (
    PositionRequest,
    RiskAssessment,
    RiskContext,
    RiskDecision,
    RiskLimits,
    RiskReason,
)

_ZERO = Decimal("0")


@dataclass(slots=True)
class KillSwitch:
    """Explicit manual safety state checked before every exposure increase."""

    engaged: bool = True

    def engage(self) -> None:
        """Immediately block new/increased exposure."""
        self.engaged = True

    def disengage(self) -> None:
        """Allow evaluation to continue; all other risk checks remain mandatory."""
        self.engaged = False


class RiskEngine:
    """Apply mandatory health, loss, correlation, and sizing limits centrally."""

    def __init__(self, limits: RiskLimits, kill_switch: KillSwitch) -> None:
        self._limits = limits
        self._kill_switch = kill_switch

    @property
    def kill_switch_engaged(self) -> bool:
        """Expose the authoritative kill-switch state for cross-module consistency checks."""

        return self._kill_switch.engaged

    def evaluate(self, request: PositionRequest, context: RiskContext) -> RiskAssessment:
        """Approve, reduce, or reject a proposed increase in spot long exposure."""
        blocking_reason = self._blocking_reason(request, context)
        if blocking_reason is not None:
            return _reject(blocking_reason)

        approved_notional = request.requested_notional
        limiting_reasons: list[RiskReason] = []

        risk_budget = context.equity * self._limits.max_risk_per_trade_fraction
        if request.risk_at_stop > risk_budget:
            risk_capped = request.requested_notional * risk_budget / request.risk_at_stop
            approved_notional = min(approved_notional, risk_capped)
            limiting_reasons.append(RiskReason.TRADE_RISK_LIMIT)

        total_cap = context.equity * self._limits.max_total_exposure_fraction
        remaining_total = max(_ZERO, total_cap - context.gross_exposure)
        if approved_notional > remaining_total:
            approved_notional = remaining_total
            limiting_reasons.append(RiskReason.TOTAL_EXPOSURE_LIMIT)

        symbol_cap = context.equity * self._limits.max_symbol_exposure_fraction
        remaining_symbol = max(_ZERO, symbol_cap - context.symbol_exposure)
        if approved_notional > remaining_symbol:
            approved_notional = remaining_symbol
            limiting_reasons.append(RiskReason.SYMBOL_EXPOSURE_LIMIT)

        if approved_notional <= _ZERO:
            reasons = tuple(limiting_reasons) or (RiskReason.TOTAL_EXPOSURE_LIMIT,)
            return RiskAssessment(RiskDecision.REJECT, _ZERO, reasons)

        if approved_notional < request.requested_notional:
            return RiskAssessment(
                decision=RiskDecision.REDUCE,
                approved_notional=approved_notional,
                reasons=tuple(limiting_reasons),
            )

        return RiskAssessment(
            decision=RiskDecision.APPROVE,
            approved_notional=request.requested_notional,
            reasons=(),
        )

    def _blocking_reason(
        self,
        request: PositionRequest,
        context: RiskContext,
    ) -> RiskReason | None:
        if self._kill_switch.engaged:
            return RiskReason.KILL_SWITCH
        if context.equity == _ZERO:
            return RiskReason.ACCOUNT_DEPLETED
        if not context.reconciliation_ok:
            return RiskReason.RECONCILIATION_ERROR
        if context.market_data_age_ms > self._limits.max_market_data_age_ms:
            return RiskReason.STALE_MARKET_DATA
        if context.daily_loss_fraction >= self._limits.max_daily_loss_fraction:
            return RiskReason.DAILY_LOSS_LIMIT
        if context.drawdown_fraction >= self._limits.max_drawdown_fraction:
            return RiskReason.DRAWDOWN_LIMIT
        if request.opens_new_position and context.open_positions >= self._limits.max_open_positions:
            return RiskReason.MAX_OPEN_POSITIONS
        if context.max_abs_correlation >= self._limits.max_abs_correlation:
            return RiskReason.CORRELATION_LIMIT
        return None


def _reject(reason: RiskReason) -> RiskAssessment:
    return RiskAssessment(
        decision=RiskDecision.REJECT,
        approved_notional=_ZERO,
        reasons=(reason,),
    )
