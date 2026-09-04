"""Event-ordered, cost-aware backtesting primitives."""

from .engine import BacktestEngine
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

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
    "BacktestStrategy",
    "BacktestValidationError",
    "EquityPoint",
    "Fill",
    "RoundTrip",
    "Side",
    "TargetPosition",
]
