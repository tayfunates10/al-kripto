"""Models for deterministic, non-production execution tests."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class ExecutionStatus(StrEnum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"


@dataclass(frozen=True, slots=True)
class Fill:
    quantity: Decimal
    price: Decimal

    def __post_init__(self) -> None:
        if self.quantity <= 0 or self.price <= 0:
            raise ValueError("fill quantity and price must be > 0")


@dataclass(slots=True)
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
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.quantity <= 0:
            raise ValueError("quantity must be > 0")

    @property
    def filled_quantity(self) -> Decimal:
        return sum((fill.quantity for fill in self.fills), Decimal("0"))

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity
