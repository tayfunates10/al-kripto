"""Deterministic execution engine for paper/test-environment validation only."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from .models import ExecutionOrder, ExecutionStatus, Fill, Side


class TestExecutionEngine:
    """In-memory execution simulator with idempotent client order IDs."""

    def __init__(self) -> None:
        self._orders: dict[str, ExecutionOrder] = {}

    def submit(
        self,
        *,
        client_order_id: str,
        symbol: str,
        side: Side,
        quantity: Decimal,
    ) -> ExecutionOrder:
        existing = self._orders.get(client_order_id)
        if existing is not None:
            same_order = (
                existing.symbol == symbol
                and existing.side is side
                and existing.quantity == quantity
            )
            if not same_order:
                raise ValueError("client_order_id already exists with different order parameters")
            return existing

        order = ExecutionOrder(
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
        )
        self._orders[client_order_id] = order
        return order

    def apply_fill(
        self,
        client_order_id: str,
        *,
        quantity: Decimal,
        price: Decimal,
    ) -> ExecutionOrder:
        order = self._require_order(client_order_id)
        if order.status in {ExecutionStatus.CANCELED, ExecutionStatus.FILLED}:
            raise ValueError("terminal order cannot receive fills")

        fill = Fill(quantity=quantity, price=price)
        if fill.quantity > order.remaining_quantity:
            raise ValueError("fill exceeds remaining quantity")

        updated = replace(order, fills=(*order.fills, fill))
        updated = replace(
            updated,
            status=(
                ExecutionStatus.FILLED
                if updated.remaining_quantity == Decimal("0")
                else ExecutionStatus.PARTIALLY_FILLED
            ),
        )
        self._orders[client_order_id] = updated
        return updated

    def cancel(self, client_order_id: str) -> ExecutionOrder:
        order = self._require_order(client_order_id)
        if order.status is ExecutionStatus.FILLED:
            raise ValueError("filled order cannot be canceled")
        if order.status is ExecutionStatus.CANCELED:
            return order

        updated = replace(order, status=ExecutionStatus.CANCELED)
        self._orders[client_order_id] = updated
        return updated

    def get(self, client_order_id: str) -> ExecutionOrder:
        return self._require_order(client_order_id)

    def _require_order(self, client_order_id: str) -> ExecutionOrder:
        try:
            return self._orders[client_order_id]
        except KeyError as error:
            raise KeyError(f"unknown client_order_id: {client_order_id}") from error
