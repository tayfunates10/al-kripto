"""Tests for safe test-environment execution."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import cast

from al_kripto.execution import ExecutionStatus, Side, TestExecutionEngine


class TestExecutionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = TestExecutionEngine()

    def test_submit_is_idempotent_for_same_client_order_id(self) -> None:
        first = self.engine.submit(
            client_order_id="order-1",
            symbol="BTCUSDT",
            side=Side.BUY,
            quantity=Decimal("1"),
        )
        second = self.engine.submit(
            client_order_id="order-1",
            symbol="BTCUSDT",
            side=Side.BUY,
            quantity=Decimal("1"),
        )
        self.assertIs(first, second)

    def test_returned_order_cannot_mutate_engine_state(self) -> None:
        order = self.engine.submit(
            client_order_id="immutable-1",
            symbol="BTCUSDT",
            side=Side.BUY,
            quantity=Decimal("1"),
        )

        with self.assertRaises(FrozenInstanceError):
            setattr(order, "status", ExecutionStatus.FILLED)
        with self.assertRaises(FrozenInstanceError):
            setattr(order, "quantity", Decimal("999999"))

        stored = self.engine.get("immutable-1")
        self.assertEqual(stored.status, ExecutionStatus.NEW)
        self.assertEqual(stored.quantity, Decimal("1"))

    def test_duplicate_id_with_different_parameters_is_rejected(self) -> None:
        self.engine.submit(
            client_order_id="order-1",
            symbol="BTCUSDT",
            side=Side.BUY,
            quantity=Decimal("1"),
        )
        with self.assertRaises(ValueError):
            self.engine.submit(
                client_order_id="order-1",
                symbol="ETHUSDT",
                side=Side.BUY,
                quantity=Decimal("1"),
            )

    def test_invalid_symbol_is_rejected(self) -> None:
        for symbol in ("x", "btc usdt", " BTCUSDT ", "'; DROP TABLE--"):
            with self.subTest(symbol=symbol):
                with self.assertRaises(ValueError):
                    self.engine.submit(
                        client_order_id=f"bad-{symbol}",
                        symbol=symbol,
                        side=Side.BUY,
                        quantity=Decimal("1"),
                    )

    def test_non_decimal_quantity_is_rejected_before_storage(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.submit(
                client_order_id="float-order",
                symbol="BTCUSDT",
                side=Side.BUY,
                quantity=cast(Decimal, 0.1),
            )
        with self.assertRaises(KeyError):
            self.engine.get("float-order")

    def test_partial_fill_then_full_fill(self) -> None:
        original = self.engine.submit(
            client_order_id="order-2",
            symbol="BTCUSDT",
            side=Side.BUY,
            quantity=Decimal("2"),
        )
        partial = self.engine.apply_fill("order-2", quantity=Decimal("0.5"), price=Decimal("100"))
        self.assertEqual(partial.status, ExecutionStatus.PARTIALLY_FILLED)
        self.assertEqual(partial.remaining_quantity, Decimal("1.5"))
        self.assertEqual(original.status, ExecutionStatus.NEW)

        filled = self.engine.apply_fill("order-2", quantity=Decimal("1.5"), price=Decimal("101"))
        self.assertEqual(filled.status, ExecutionStatus.FILLED)
        self.assertEqual(filled.remaining_quantity, Decimal("0"))

    def test_non_decimal_fill_is_rejected_without_mutating_order(self) -> None:
        original = self.engine.submit(
            client_order_id="float-fill",
            symbol="BTCUSDT",
            side=Side.BUY,
            quantity=Decimal("1"),
        )

        with self.assertRaises(ValueError):
            self.engine.apply_fill(
                "float-fill",
                quantity=cast(Decimal, 0.1),
                price=cast(Decimal, 100.0),
            )

        self.assertIs(self.engine.get("float-fill"), original)
        self.assertEqual(original.fills, ())

    def test_overfill_is_rejected(self) -> None:
        self.engine.submit(
            client_order_id="order-3",
            symbol="BTCUSDT",
            side=Side.BUY,
            quantity=Decimal("1"),
        )
        with self.assertRaises(ValueError):
            self.engine.apply_fill("order-3", quantity=Decimal("2"), price=Decimal("100"))

    def test_cancel_blocks_future_fill(self) -> None:
        original = self.engine.submit(
            client_order_id="order-4",
            symbol="BTCUSDT",
            side=Side.SELL,
            quantity=Decimal("1"),
        )
        canceled = self.engine.cancel("order-4")
        self.assertEqual(canceled.status, ExecutionStatus.CANCELED)
        self.assertEqual(original.status, ExecutionStatus.NEW)
        with self.assertRaises(ValueError):
            self.engine.apply_fill("order-4", quantity=Decimal("1"), price=Decimal("100"))


if __name__ == "__main__":
    unittest.main()
