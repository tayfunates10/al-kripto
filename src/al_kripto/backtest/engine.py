"""Cost-aware long/flat backtest engine with explicit event ordering."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Sequence
from decimal import ROUND_DOWN, Decimal
from itertools import pairwise
from typing import overload

from al_kripto.market_data import Candle

from .models import (
    BacktestConfig,
    BacktestResult,
    BacktestValidationError,
    EquityPoint,
    Fill,
    RoundTrip,
    Side,
    TargetPosition,
)
from .strategy import BacktestStrategy

_ZERO = Decimal("0")
_ONE = Decimal("1")


class _HistoryView(Sequence[Candle]):
    """Immutable prefix view over a candle tuple without copying the full history."""

    __slots__ = ("_series", "_stop")

    def __init__(self, series: tuple[Candle, ...], stop: int) -> None:
        self._series = series
        self._stop = stop

    def __len__(self) -> int:
        return self._stop

    @overload
    def __getitem__(self, index: int) -> Candle: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[Candle, ...]: ...

    def __getitem__(self, index: int | slice) -> Candle | tuple[Candle, ...]:
        if isinstance(index, slice):
            start, stop, step = index.indices(self._stop)
            return tuple(self._series[position] for position in range(start, stop, step))

        normalized = index + self._stop if index < 0 else index
        if normalized < 0 or normalized >= self._stop:
            raise IndexError("history index out of range")
        return self._series[normalized]


class BacktestEngine:
    """Run deterministic next-open simulations without future-data access."""

    def __init__(
        self,
        config: BacktestConfig | None = None,
        *,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        self._config = config or BacktestConfig()
        self._clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)

    def run(self, candles: Iterable[Candle], strategy: BacktestStrategy) -> BacktestResult:
        series = tuple(candles)
        self._validate_series(series)

        cash = self._config.initial_cash
        quantity = _ZERO
        position = TargetPosition.FLAT
        pending_target: TargetPosition | None = None
        entry_fill: Fill | None = None
        paid_fees = _ZERO
        fills: list[Fill] = []
        round_trips: list[RoundTrip] = []
        equity_curve: list[EquityPoint] = []
        peak_equity = self._config.initial_cash
        max_drawdown = _ZERO

        for index, candle in enumerate(series):
            if pending_target is not None and pending_target is not position:
                if pending_target is TargetPosition.LONG:
                    fill, cash, quantity = self._buy(candle, cash)
                    position = TargetPosition.LONG
                    entry_fill = fill
                else:
                    if entry_fill is None:
                        raise BacktestValidationError("Cannot exit without an entry fill.")
                    fill, cash = self._sell(candle, cash, quantity)
                    position = TargetPosition.FLAT
                    quantity = _ZERO
                    round_trips.append(self._round_trip(entry_fill, fill))
                    entry_fill = None

                paid_fees += fill.fee
                fills.append(fill)

            equity = cash + (quantity * candle.close)
            peak_equity = max(peak_equity, equity)
            drawdown = _ZERO if peak_equity == _ZERO else (peak_equity - equity) / peak_equity
            max_drawdown = max(max_drawdown, drawdown)
            equity_curve.append(
                EquityPoint(
                    timestamp_ms=candle.close_time_ms,
                    equity=equity,
                    drawdown=drawdown,
                )
            )

            next_target = strategy.target_position(_HistoryView(series, index + 1))
            if not isinstance(next_target, TargetPosition):
                raise BacktestValidationError("Strategy must return TargetPosition.")
            pending_target = next_target

        final_equity = cash + (quantity * series[-1].close)
        return BacktestResult(
            initial_cash=self._config.initial_cash,
            final_cash=cash,
            final_position_quantity=quantity,
            final_equity=final_equity,
            paid_fees=paid_fees,
            max_drawdown=max_drawdown,
            fills=tuple(fills),
            round_trips=tuple(round_trips),
            equity_curve=tuple(equity_curve),
        )

    def _buy(self, candle: Candle, cash: Decimal) -> tuple[Fill, Decimal, Decimal]:
        quantity_step = self._config.quantity_step
        if quantity_step is None:
            raise BacktestValidationError(
                "quantity_step must be configured before a backtest can open a position."
            )

        execution_price = candle.open * (_ONE + self._config.slippage_rate)
        raw_quantity = cash / (execution_price * (_ONE + self._config.fee_rate))
        quantity = _round_down_to_step(raw_quantity, quantity_step)
        if quantity <= _ZERO:
            raise BacktestValidationError(
                "Rounded quantity is zero; cash is below the quantity step."
            )

        notional = quantity * execution_price
        fee = notional * self._config.fee_rate
        spent = notional + fee
        fill = Fill(
            side=Side.BUY,
            timestamp_ms=candle.open_time_ms,
            quantity=quantity,
            reference_price=candle.open,
            execution_price=execution_price,
            notional=notional,
            fee=fee,
        )
        return fill, cash - spent, quantity

    def _sell(self, candle: Candle, cash: Decimal, quantity: Decimal) -> tuple[Fill, Decimal]:
        execution_price = candle.open * (_ONE - self._config.slippage_rate)
        notional = quantity * execution_price
        fee = notional * self._config.fee_rate
        fill = Fill(
            side=Side.SELL,
            timestamp_ms=candle.open_time_ms,
            quantity=quantity,
            reference_price=candle.open,
            execution_price=execution_price,
            notional=notional,
            fee=fee,
        )
        return fill, cash + notional - fee

    @staticmethod
    def _round_trip(entry: Fill, exit_fill: Fill) -> RoundTrip:
        gross_pnl = entry.quantity * (exit_fill.execution_price - entry.execution_price)
        net_pnl = gross_pnl - entry.fee - exit_fill.fee
        return RoundTrip(
            entry=entry,
            exit=exit_fill,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
        )

    def _validate_series(self, series: tuple[Candle, ...]) -> None:
        if not series:
            raise BacktestValidationError("Backtest requires at least one candle.")
        symbol = series[0].symbol
        interval = series[0].interval
        if any(candle.symbol != symbol for candle in series):
            raise BacktestValidationError("All candles must use the same symbol.")
        if any(candle.interval != interval for candle in series):
            raise BacktestValidationError("All candles must use the same interval metadata.")
        if any(
            current.open_time_ms <= previous.close_time_ms for previous, current in pairwise(series)
        ):
            raise BacktestValidationError("Candles must be chronological and non-overlapping.")

        as_of_ms = self._clock_ms()
        if as_of_ms < 0:
            raise BacktestValidationError("Backtest clock must be non-negative.")
        if any(candle.close_time_ms > as_of_ms for candle in series):
            raise BacktestValidationError(
                "Backtest requires fully closed candles; in-progress candles are not allowed."
            )


def _round_down_to_step(quantity: Decimal, step: Decimal) -> Decimal:
    units = (quantity / step).to_integral_value(rounding=ROUND_DOWN)
    return units * step
