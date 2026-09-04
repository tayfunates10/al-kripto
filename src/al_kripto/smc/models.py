"""Auditable models emitted by the deterministic SMC research engine."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class SMCValidationError(ValueError):
    """Raised when an SMC event violates structural invariants."""


class Direction(StrEnum):
    """Directional label for research events."""

    BULLISH = "bullish"
    BEARISH = "bearish"


class SwingKind(StrEnum):
    """Confirmed local extremum type."""

    HIGH = "high"
    LOW = "low"


class BreakKind(StrEnum):
    """Market-structure break label."""

    BOS = "bos"
    CHOCH = "choch"


def _validate_positive_price(value: Decimal, field_name: str) -> None:
    if not value.is_finite() or value <= 0:
        raise SMCValidationError(f"{field_name} must be finite and > 0.")


def _validate_index(value: int, field_name: str) -> None:
    if value < 0:
        raise SMCValidationError(f"{field_name} must be >= 0.")


@dataclass(frozen=True, slots=True)
class SwingPoint:
    """Swing that becomes usable only after right-side confirmation candles close."""

    kind: SwingKind
    index: int
    price: Decimal
    occurred_at_ms: int
    confirmed_index: int
    confirmed_at_ms: int

    def __post_init__(self) -> None:
        _validate_index(self.index, "index")
        _validate_index(self.confirmed_index, "confirmed_index")
        _validate_positive_price(self.price, "price")
        if self.confirmed_index <= self.index:
            raise SMCValidationError("confirmed_index must be later than the swing index.")
        if self.occurred_at_ms < 0 or self.confirmed_at_ms < self.occurred_at_ms:
            raise SMCValidationError("Swing timestamps are inconsistent.")


@dataclass(frozen=True, slots=True)
class LiquiditySweep:
    """Wick through a confirmed swing followed by a close back inside the level."""

    direction: Direction
    index: int
    swing_index: int
    level: Decimal
    event_time_ms: int

    def __post_init__(self) -> None:
        _validate_index(self.index, "index")
        _validate_index(self.swing_index, "swing_index")
        _validate_positive_price(self.level, "level")
        if self.event_time_ms < 0:
            raise SMCValidationError("event_time_ms must be >= 0.")


@dataclass(frozen=True, slots=True)
class StructureBreak:
    """Close beyond a previously confirmed swing level."""

    kind: BreakKind
    direction: Direction
    index: int
    swing_index: int
    level: Decimal
    event_time_ms: int

    def __post_init__(self) -> None:
        _validate_index(self.index, "index")
        _validate_index(self.swing_index, "swing_index")
        _validate_positive_price(self.level, "level")
        if self.event_time_ms < 0:
            raise SMCValidationError("event_time_ms must be >= 0.")


@dataclass(frozen=True, slots=True)
class FairValueGap:
    """Three-candle non-overlap zone."""

    direction: Direction
    index: int
    lower: Decimal
    upper: Decimal
    event_time_ms: int

    def __post_init__(self) -> None:
        _validate_index(self.index, "index")
        _validate_positive_price(self.lower, "lower")
        _validate_positive_price(self.upper, "upper")
        if self.lower >= self.upper:
            raise SMCValidationError("Gap lower bound must be below upper bound.")
        if self.event_time_ms < 0:
            raise SMCValidationError("event_time_ms must be >= 0.")


@dataclass(frozen=True, slots=True)
class OrderBlock:
    """Last opposite candle before a confirmed structure break."""

    direction: Direction
    index: int
    lower: Decimal
    upper: Decimal
    confirmed_by_index: int
    event_time_ms: int

    def __post_init__(self) -> None:
        _validate_index(self.index, "index")
        _validate_index(self.confirmed_by_index, "confirmed_by_index")
        _validate_positive_price(self.lower, "lower")
        _validate_positive_price(self.upper, "upper")
        if self.lower >= self.upper:
            raise SMCValidationError("Order-block lower bound must be below upper bound.")
        if self.confirmed_by_index <= self.index:
            raise SMCValidationError("Order block must be confirmed by a later break candle.")
        if self.event_time_ms < 0:
            raise SMCValidationError("event_time_ms must be >= 0.")


@dataclass(frozen=True, slots=True)
class SMCAnalysis:
    """Complete deterministic structure analysis for one candle sequence."""

    swings: tuple[SwingPoint, ...]
    sweeps: tuple[LiquiditySweep, ...]
    breaks: tuple[StructureBreak, ...]
    fair_value_gaps: tuple[FairValueGap, ...]
    order_blocks: tuple[OrderBlock, ...]
