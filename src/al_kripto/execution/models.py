"""Models for deterministic, non-production execution tests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, StrEnum

_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")
_ZERO = Decimal("0")


class Side(Enum):
    """Execution-engine side; intentionally not string-comparable across domains."""

    BUY = "buy"
    SELL = "sell"


class ExecutionStatus(StrEnum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"


def _require_positive_decimal(value: object, field_name: str) -> None:
    if not isinstance(value, Decimal):
        raise ValueError(f"{field_name} must be Decimal")
    if not value.is_finite() or value <= _ZERO:
        raise ValueError(f"{field_name} must be finite and > 0")


@dataclass(frozen=True, slots=True)
class Fill:
    quantity: Decimal
    price: Decimal

    def __post_init__(self) -> None:
        _require_positive_decimal(self.quantity, "fill quantity")
        _require_positive_decimal(self.price, "fill price")


@dataclass(frozen=True, slots=True)
class ExecutionOrder:
    client_order_id: str
    symbol: str
    side: Side
    quantity: Decimal
    status: ExecutionStatus = ExecutionStatus.NEW
    fills: tuple[Fill, ...] = ()

    def __post_init__(self) -> None:
        if not self.client_order_id.strip():
            raise ValueError("client_order_id must not be empty")
        if not _SYMBOL_PATTERN.fullmatch(self.symbol):
            raise ValueError(f"invalid execution symbol: {self.symbol!r}")
        if not isinstance(self.side, Side):
            raise ValueError("side must be an execution Side")
        _require_positive_decimal(self.quantity, "quantity")

    @property
    def filled_quantity(self) -> Decimal:
        return sum((fill.quantity for fill in self.fills), _ZERO)

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity
