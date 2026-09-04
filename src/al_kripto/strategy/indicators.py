"""Small Decimal-based indicators used by deterministic baseline strategies."""

from __future__ import annotations

from decimal import Decimal
from itertools import pairwise

from al_kripto.market_data import Candle

_ZERO = Decimal("0")


def simple_moving_average(values: tuple[Decimal, ...]) -> Decimal:
    """Return the arithmetic mean of a non-empty Decimal series."""
    if not values:
        raise ValueError("values must not be empty.")
    return sum(values, _ZERO) / Decimal(len(values))


def volume_weighted_price(candles: tuple[Candle, ...]) -> Decimal | None:
    """Return close-price VWAP, or None when the whole window has zero volume."""
    if not candles:
        raise ValueError("candles must not be empty.")
    total_volume = sum((candle.volume for candle in candles), _ZERO)
    if total_volume == _ZERO:
        return None
    weighted = sum((candle.close * candle.volume for candle in candles), _ZERO)
    return weighted / total_volume


def mean_absolute_return(closes: tuple[Decimal, ...]) -> Decimal:
    """Return mean absolute close-to-close simple return for at least two closes."""
    if len(closes) < 2:
        raise ValueError("at least two closes are required.")

    returns: list[Decimal] = []
    for previous, current in pairwise(closes):
        if previous <= _ZERO:
            raise ValueError("close prices must be > 0.")
        returns.append(abs((current / previous) - Decimal("1")))
    return simple_moving_average(tuple(returns))
