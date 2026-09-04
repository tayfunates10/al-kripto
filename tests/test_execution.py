"""Tests for safe test-environment execution."""

from __future__ import annotations

import unittest
from decimal import Decimal

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

    def test_partial_fill_then_full_fill(self) -> None:
        self.engine.submit(
            client_order_id="order-2",
            symbol="BTCUSDT",
            side=Side.BUY,
            quantity=Decimal("2"),
        )
        partial = self.engine.apply_fill("order-2", quantity=Decimal("0.5"), price=Decimal("100"))
        self.assertEqual(partial.status, ExecutionStatus.PARTIALLY_FILLED)
        self.assertEqual(partial.remaining_quantity, Decimal("1.5"))

        filled = self.engine.apply_fill("order-2", quantity=Decimal("1.5"), price=Decimal("101"))
        self.assertEqual(filled.status, ExecutionStatus.FILLED)
        self.assertEqual(filled.remaining_quantity, Decimal("0"))

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
        self.engine.submit(
            client_order_id="order-4",
            symbol="BTCUSDT",
            side=Side.SELL,
            quantity=Decimal("1"),
        )
        canceled = self.engine.cancel("order-4")
        self.assertEqual(canceled.status, ExecutionStatus.CANCELED)
        with self.assertRaises(ValueError):
            self.engine.apply_fill("order-4", quantity=Decimal("1"), price=Decimal("100"))


if __name__ == "__main__":
    unittest.main()
