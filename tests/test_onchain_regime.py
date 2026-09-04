"""Tests for point-in-time-safe on-chain research regimes."""

from __future__ import annotations

import unittest
from decimal import Decimal

from al_kripto.onchain import (
    MetricName,
    MetricObservation,
    OnChainRegime,
    OnChainRegimeConfig,
    OnChainRegimeEngine,
    OnChainSnapshot,
    OnChainValidationError,
)


def observation(
    metric: MetricName,
    percentile: str,
    *,
    observed_at_ms: int = 1_000,
    available_at_ms: int = 2_000,
) -> MetricObservation:
    return MetricObservation(
        metric=metric,
        value=Decimal("1.5"),
        percentile=Decimal(percentile),
        observed_at_ms=observed_at_ms,
        available_at_ms=available_at_ms,
    )


def btc_snapshot(percentiles: tuple[str, str, str, str]) -> OnChainSnapshot:
    metrics = tuple(MetricName)
    return OnChainSnapshot(
        asset="BTC",
        observations=tuple(
            observation(metric, percentile)
            for metric, percentile in zip(metrics, percentiles, strict=True)
        ),
    )


class OnChainModelTests(unittest.TestCase):
    def test_rejects_percentile_outside_unit_interval(self) -> None:
        with self.assertRaises(OnChainValidationError):
            observation(MetricName.MVRV, "1.01")

    def test_rejects_duplicate_metrics(self) -> None:
        with self.assertRaises(OnChainValidationError):
            OnChainSnapshot(
                asset="BTC",
                observations=(
                    observation(MetricName.MVRV, "0.4"),
                    observation(MetricName.MVRV, "0.5"),
                ),
            )

    def test_rejects_puell_for_non_btc_asset(self) -> None:
        with self.assertRaises(OnChainValidationError):
            OnChainSnapshot(
                asset="ETH",
                observations=(observation(MetricName.PUELL_MULTIPLE, "0.5"),),
            )

    def test_rejects_publication_before_observation(self) -> None:
        with self.assertRaises(OnChainValidationError):
            observation(
                MetricName.SOPR,
                "0.5",
                observed_at_ms=2_000,
                available_at_ms=1_999,
            )


class OnChainRegimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = OnChainRegimeEngine(
            OnChainRegimeConfig(max_age_ms=10_000, minimum_metrics=3)
        )

    def test_classifies_high_consensus_as_overheated(self) -> None:
        result = self.engine.classify(
            btc_snapshot(("0.90", "0.85", "0.95", "0.40")),
            decision_time_ms=2_500,
        )
        self.assertEqual(result.regime, OnChainRegime.OVERHEATED)

    def test_classifies_low_consensus_as_underheated(self) -> None:
        result = self.engine.classify(
            btc_snapshot(("0.10", "0.15", "0.05", "0.50")),
            decision_time_ms=2_500,
        )
        self.assertEqual(result.regime, OnChainRegime.UNDERHEATED)

    def test_mixed_percentiles_are_neutral(self) -> None:
        result = self.engine.classify(
            btc_snapshot(("0.10", "0.50", "0.90", "0.55")),
            decision_time_ms=2_500,
        )
        self.assertEqual(result.regime, OnChainRegime.NEUTRAL)

    def test_future_publication_is_excluded_and_fails_closed(self) -> None:
        snapshot = OnChainSnapshot(
            asset="BTC",
            observations=(
                observation(MetricName.MVRV, "0.90", available_at_ms=2_000),
                observation(MetricName.SOPR, "0.90", available_at_ms=2_000),
                observation(MetricName.PUELL_MULTIPLE, "0.90", available_at_ms=3_000),
                observation(MetricName.NVT, "0.90", available_at_ms=3_000),
            ),
        )

        result = self.engine.classify(snapshot, decision_time_ms=2_500)

        self.assertEqual(result.regime, OnChainRegime.UNKNOWN)
        self.assertEqual(
            result.excluded_metrics,
            (MetricName.PUELL_MULTIPLE, MetricName.NVT),
        )

    def test_stale_observations_are_excluded(self) -> None:
        snapshot = btc_snapshot(("0.90", "0.90", "0.90", "0.90"))

        result = self.engine.classify(snapshot, decision_time_ms=20_001)

        self.assertEqual(result.regime, OnChainRegime.UNKNOWN)
        self.assertEqual(result.usable_metrics, ())

    def test_invalid_threshold_order_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            OnChainRegimeConfig(
                low_percentile=Decimal("0.80"),
                high_percentile=Decimal("0.20"),
            )


if __name__ == "__main__":
    unittest.main()
