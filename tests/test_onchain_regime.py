"""Tests for point-in-time-safe on-chain research regimes."""

from __future__ import annotations

import unittest
from decimal import Decimal

from al_kripto.onchain import (
    MetricName,
    MetricObservation,
    OnChainRegime,
    OnChainRegimeAssessment,
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
            OnChainRegimeConfig(
                max_age_ms=10_000,
                max_observation_age_ms=10_000,
                minimum_metrics=3,
                consensus_metrics=3,
            )
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

    def test_stale_publication_is_excluded(self) -> None:
        snapshot = btc_snapshot(("0.90", "0.90", "0.90", "0.90"))

        result = self.engine.classify(snapshot, decision_time_ms=20_001)

        self.assertEqual(result.regime, OnChainRegime.UNKNOWN)
        self.assertEqual(result.usable_metrics, ())

    def test_recent_publication_cannot_hide_stale_observation(self) -> None:
        now = 100 * 86_400_000
        stale_observed = now - (90 * 86_400_000)
        recent_available = now - 1_000
        snapshot = OnChainSnapshot(
            asset="BTC",
            observations=(
                observation(
                    MetricName.MVRV,
                    "0.95",
                    observed_at_ms=stale_observed,
                    available_at_ms=recent_available,
                ),
                observation(
                    MetricName.SOPR,
                    "0.95",
                    observed_at_ms=now - 2_000,
                    available_at_ms=now - 1_000,
                ),
                observation(
                    MetricName.PUELL_MULTIPLE,
                    "0.95",
                    observed_at_ms=now - 2_000,
                    available_at_ms=now - 1_000,
                ),
            ),
        )
        engine = OnChainRegimeEngine(
            OnChainRegimeConfig(
                minimum_metrics=3,
                consensus_metrics=3,
                max_age_ms=10_000,
                max_observation_age_ms=86_400_000,
            )
        )

        result = engine.classify(snapshot, decision_time_ms=now)

        self.assertEqual(result.regime, OnChainRegime.UNKNOWN)
        self.assertEqual(result.usable_metrics, (MetricName.SOPR, MetricName.PUELL_MULTIPLE))
        self.assertEqual(result.excluded_metrics, (MetricName.MVRV,))

    def test_consensus_threshold_is_independent_from_minimum_data_threshold(self) -> None:
        engine = OnChainRegimeEngine(
            OnChainRegimeConfig(
                minimum_metrics=2,
                consensus_metrics=3,
                max_age_ms=10_000,
                max_observation_age_ms=10_000,
            )
        )

        result = engine.classify(
            btc_snapshot(("0.95", "0.95", "0.50", "0.50")),
            decision_time_ms=2_500,
        )

        self.assertEqual(result.regime, OnChainRegime.NEUTRAL)

    def test_invalid_threshold_order_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            OnChainRegimeConfig(
                low_percentile=Decimal("0.80"),
                high_percentile=Decimal("0.20"),
            )

    def test_assessment_rejects_overlapping_metric_groups(self) -> None:
        with self.assertRaises(ValueError):
            OnChainRegimeAssessment(
                regime=OnChainRegime.UNKNOWN,
                decision_time_ms=1,
                usable_metrics=(MetricName.MVRV,),
                excluded_metrics=(MetricName.MVRV,),
            )

    def test_assessment_rejects_negative_decision_time(self) -> None:
        with self.assertRaises(ValueError):
            OnChainRegimeAssessment(
                regime=OnChainRegime.UNKNOWN,
                decision_time_ms=-1,
                usable_metrics=(),
                excluded_metrics=(),
            )


if __name__ == "__main__":
    unittest.main()
