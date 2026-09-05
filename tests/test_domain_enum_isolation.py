"""Regression tests preventing accidental cross-domain enum equality."""

from __future__ import annotations

import unittest

from al_kripto.backtest import Side as BacktestSide
from al_kripto.execution import Side as ExecutionSide


class DomainEnumIsolationTests(unittest.TestCase):
    def test_backtest_and_execution_sides_are_not_equal(self) -> None:
        self.assertNotEqual(BacktestSide.BUY, ExecutionSide.BUY)
        self.assertNotEqual(BacktestSide.SELL, ExecutionSide.SELL)
        self.assertEqual(BacktestSide.BUY.value, ExecutionSide.BUY.value)


if __name__ == "__main__":
    unittest.main()
