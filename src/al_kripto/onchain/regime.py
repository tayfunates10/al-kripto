"""Deterministic, point-in-time-safe on-chain research regime classification."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .models import MetricName, MetricObservation, OnChainSnapshot


class OnChainRegime(StrEnum):
    """Descriptive research regimes; these are not trading instructions."""

    UNKNOWN = "unknown"
    UNDERHEATED = "underheated"
    NEUTRAL = "neutral"
    OVERHEATED = "overheated"


@dataclass(frozen=True, slots=True)
class OnChainRegimeConfig:
    """Thresholds for percentile-consensus classification."""

    low_percentile: Decimal = Decimal("0.20")
    high_percentile: Decimal = Decimal("0.80")
    minimum_metrics: int = 3
    max_age_ms: int = 172_800_000

    def __post_init__(self) -> None:
        if not self.low_percentile.is_finite() or not self.high_percentile.is_finite():
            raise ValueError("Percentile thresholds must be finite.")
        if not Decimal("0") <= self.low_percentile < self.high_percentile <= Decimal("1"):
            raise ValueError("Percentile thresholds must satisfy 0 <= low < high <= 1.")
        if not 1 <= self.minimum_metrics <= len(MetricName):
            raise ValueError("minimum_metrics must be between 1 and the supported metric count.")
        if self.max_age_ms <= 0:
            raise ValueError("max_age_ms must be > 0.")


@dataclass(frozen=True, slots=True)
class OnChainRegimeAssessment:
    """Auditable result of one point-in-time regime assessment."""

    regime: OnChainRegime
    decision_time_ms: int
    usable_metrics: tuple[MetricName, ...]
    excluded_metrics: tuple[MetricName, ...]


class OnChainRegimeEngine:
    """Classify percentile consensus without exposing future or stale observations."""

    def __init__(self, config: OnChainRegimeConfig | None = None) -> None:
        self._config = config or OnChainRegimeConfig()

    def classify(
        self,
        snapshot: OnChainSnapshot,
        *,
        decision_time_ms: int,
    ) -> OnChainRegimeAssessment:
        if decision_time_ms < 0:
            raise ValueError("decision_time_ms must be >= 0.")

        usable: list[MetricObservation] = []
        excluded: list[MetricName] = []
        for observation in snapshot.observations:
            if observation.available_at_ms > decision_time_ms:
                excluded.append(observation.metric)
                continue
            age_ms = decision_time_ms - observation.available_at_ms
            if age_ms > self._config.max_age_ms:
                excluded.append(observation.metric)
                continue
            usable.append(observation)

        usable_names = tuple(observation.metric for observation in usable)
        excluded_names = tuple(excluded)
        if len(usable) < self._config.minimum_metrics:
            return OnChainRegimeAssessment(
                regime=OnChainRegime.UNKNOWN,
                decision_time_ms=decision_time_ms,
                usable_metrics=usable_names,
                excluded_metrics=excluded_names,
            )

        high_count = sum(
            observation.percentile >= self._config.high_percentile for observation in usable
        )
        low_count = sum(
            observation.percentile <= self._config.low_percentile for observation in usable
        )

        if high_count >= self._config.minimum_metrics:
            regime = OnChainRegime.OVERHEATED
        elif low_count >= self._config.minimum_metrics:
            regime = OnChainRegime.UNDERHEATED
        else:
            regime = OnChainRegime.NEUTRAL

        return OnChainRegimeAssessment(
            regime=regime,
            decision_time_ms=decision_time_ms,
            usable_metrics=usable_names,
            excluded_metrics=excluded_names,
        )
