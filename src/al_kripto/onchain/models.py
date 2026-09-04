"""Validated on-chain research data models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

_ASSET_PATTERN = re.compile(r"^[A-Z0-9]{2,12}$")
_ZERO = Decimal("0")
_ONE = Decimal("1")


class OnChainValidationError(ValueError):
    """Raised when on-chain research data violates required invariants."""


class MetricName(StrEnum):
    """On-chain metrics tracked by the initial research layer."""

    MVRV = "mvrv"
    SOPR = "sopr"
    PUELL_MULTIPLE = "puell_multiple"
    NVT = "nvt"


@dataclass(frozen=True, slots=True)
class MetricObservation:
    """One raw metric value plus its historical percentile and availability time."""

    metric: MetricName
    value: Decimal
    percentile: Decimal
    observed_at_ms: int
    available_at_ms: int

    def __post_init__(self) -> None:
        if not self.value.is_finite() or self.value <= _ZERO:
            raise OnChainValidationError("On-chain metric value must be finite and > 0.")
        if not self.percentile.is_finite() or not _ZERO <= self.percentile <= _ONE:
            raise OnChainValidationError("Metric percentile must be between 0 and 1.")
        if self.observed_at_ms < 0:
            raise OnChainValidationError("observed_at_ms must be >= 0.")
        if self.available_at_ms < self.observed_at_ms:
            raise OnChainValidationError(
                "available_at_ms cannot be earlier than the observation timestamp."
            )


@dataclass(frozen=True, slots=True)
class OnChainSnapshot:
    """A provider-neutral collection of normalized metric observations."""

    asset: str
    observations: tuple[MetricObservation, ...]

    def __post_init__(self) -> None:
        if not _ASSET_PATTERN.fullmatch(self.asset):
            raise OnChainValidationError(f"Invalid asset identifier: {self.asset!r}")
        if not self.observations:
            raise OnChainValidationError("At least one on-chain observation is required.")

        metric_names = tuple(observation.metric for observation in self.observations)
        if len(set(metric_names)) != len(metric_names):
            raise OnChainValidationError("On-chain metrics must be unique within a snapshot.")
        if MetricName.PUELL_MULTIPLE in metric_names and self.asset != "BTC":
            raise OnChainValidationError("Puell Multiple is restricted to BTC in this project.")
