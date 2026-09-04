"""VWAP + trend + volatility-regime baseline strategy."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from al_kripto.backtest import TargetPosition
from al_kripto.market_data import Candle

from .indicators import mean_absolute_return, simple_moving_average, volume_weighted_price

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class BaselineStrategyConfig:
    """Deterministic parameters for the first baseline strategy."""

    fast_window: int = 10
    slow_window: int = 30
    vwap_window: int = 20
    volatility_window: int = 20
    max_mean_absolute_return: Decimal = Decimal("0.03")

    def __post_init__(self) -> None:
        for field_name, value in (
            ("fast_window", self.fast_window),
            ("slow_window", self.slow_window),
            ("vwap_window", self.vwap_window),
            ("volatility_window", self.volatility_window),
        ):
            if value <= 0:
                raise ValueError(f"{field_name} must be > 0.")
        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be smaller than slow_window.")
        if (
            not self.max_mean_absolute_return.is_finite()
            or self.max_mean_absolute_return < _ZERO
        ):
            raise ValueError("max_mean_absolute_return must be finite and >= 0.")

    @property
    def minimum_history(self) -> int:
        return max(
            self.slow_window,
            self.vwap_window,
            self.volatility_window + 1,
        )


class BaselineStrategy:
    """Long only when price, trend and volatility filters all agree."""

    def __init__(self, config: BaselineStrategyConfig | None = None) -> None:
        self._config = config or BaselineStrategyConfig()

    def target_position(self, history: tuple[Candle, ...]) -> TargetPosition:
        if len(history) < self._config.minimum_history:
            return TargetPosition.FLAT

        closes = tuple(candle.close for candle in history)
        fast = simple_moving_average(closes[-self._config.fast_window :])
        slow = simple_moving_average(closes[-self._config.slow_window :])
        vwap = volume_weighted_price(history[-self._config.vwap_window :])
        volatility = mean_absolute_return(
            closes[-(self._config.volatility_window + 1) :]
        )

        if vwap is None:
            return TargetPosition.FLAT

        latest_close = closes[-1]
        trend_ok = fast > slow
        price_ok = latest_close > vwap
        volatility_ok = volatility <= self._config.max_mean_absolute_return

        if trend_ok and price_ok and volatility_ok:
            return TargetPosition.LONG
        return TargetPosition.FLAT
