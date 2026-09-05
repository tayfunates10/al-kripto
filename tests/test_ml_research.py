"""Tests for leakage-resistant ML research validation primitives."""

from __future__ import annotations

import unittest
from decimal import Decimal

from al_kripto.ml_research import (
    PredictionRecord,
    ResearchValidationError,
    binary_classification_metrics,
    chronological_split,
)


class ChronologicalSplitTests(unittest.TestCase):
    def test_split_preserves_order_and_purges_boundaries(self) -> None:
        split = chronological_split(
            tuple(range(20)),
            train_size=6,
            validation_size=4,
            test_size=4,
            purge_size=2,
        )

        self.assertEqual(split.train, (2, 3, 4, 5, 6, 7))
        self.assertEqual(split.validation, (10, 11, 12, 13))
        self.assertEqual(split.test, (16, 17, 18, 19))

    def test_large_input_keeps_test_set_at_newest_edge(self) -> None:
        split = chronological_split(
            tuple(range(1000)),
            train_size=100,
            validation_size=50,
            test_size=50,
            purge_size=5,
        )

        self.assertEqual(split.train[0], 790)
        self.assertEqual(split.validation[0], 895)
        self.assertEqual(split.test[0], 950)
        self.assertEqual(split.test[-1], 999)

    def test_rejects_insufficient_samples(self) -> None:
        with self.assertRaises(ResearchValidationError):
            chronological_split(
                tuple(range(10)),
                train_size=5,
                validation_size=3,
                test_size=2,
                purge_size=1,
            )

    def test_rejects_non_positive_split_sizes(self) -> None:
        with self.assertRaises(ResearchValidationError):
            chronological_split(
                tuple(range(10)),
                train_size=0,
                validation_size=3,
                test_size=2,
            )


class PredictionMetricsTests(unittest.TestCase):
    def test_metrics_are_deterministic(self) -> None:
        records = (
            PredictionRecord(1, True, True, Decimal("0.9")),
            PredictionRecord(2, False, True, Decimal("0.7")),
            PredictionRecord(3, True, False, Decimal("0.4")),
            PredictionRecord(4, False, False, Decimal("0.1")),
        )

        metrics = binary_classification_metrics(records)

        self.assertEqual(metrics["accuracy"], Decimal("0.5"))
        self.assertEqual(metrics["precision"], Decimal("0.5"))
        self.assertEqual(metrics["recall"], Decimal("0.5"))
        self.assertEqual(metrics["brier_score"], Decimal("0.2175"))

    def test_rejects_non_chronological_predictions(self) -> None:
        records = (
            PredictionRecord(2, True, True, Decimal("0.9")),
            PredictionRecord(1, False, False, Decimal("0.1")),
        )

        with self.assertRaises(ResearchValidationError):
            binary_classification_metrics(records)

    def test_rejects_invalid_score(self) -> None:
        with self.assertRaises(ResearchValidationError):
            PredictionRecord(1, True, True, Decimal("1.1"))


if __name__ == "__main__":
    unittest.main()
