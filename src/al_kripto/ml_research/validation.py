"""Leakage-resistant chronological validation primitives for ML research."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise


class ResearchValidationError(ValueError):
    """Raised when a research validation setup could leak or become ambiguous."""


@dataclass(frozen=True, slots=True)
class ChronologicalSplit[T]:
    """Purged chronological train/validation/test split."""

    train: tuple[T, ...]
    validation: tuple[T, ...]
    test: tuple[T, ...]

    def __post_init__(self) -> None:
        if not self.train or not self.validation or not self.test:
            raise ResearchValidationError("train, validation and test must all be non-empty.")


@dataclass(frozen=True, slots=True)
class PredictionRecord:
    """One out-of-sample binary prediction with an immutable event timestamp."""

    timestamp_ms: int
    actual: bool
    predicted: bool
    score: Decimal

    def __post_init__(self) -> None:
        if self.timestamp_ms < 0:
            raise ResearchValidationError("timestamp_ms must be >= 0.")
        if not self.score.is_finite() or not Decimal("0") <= self.score <= Decimal("1"):
            raise ResearchValidationError("score must be finite and between 0 and 1.")


def chronological_split[T](
    samples: Sequence[T],
    *,
    train_size: int,
    validation_size: int,
    test_size: int,
    purge_size: int = 0,
) -> ChronologicalSplit[T]:
    """Split the newest ordered window without shuffling and purge split boundaries."""
    sizes = (train_size, validation_size, test_size)
    if any(size <= 0 for size in sizes):
        raise ResearchValidationError("split sizes must be > 0.")
    if purge_size < 0:
        raise ResearchValidationError("purge_size must be >= 0.")

    required = train_size + validation_size + test_size + (2 * purge_size)
    if len(samples) < required:
        raise ResearchValidationError(
            f"not enough samples: need at least {required}, received {len(samples)}."
        )

    window_start = len(samples) - required
    train_start = window_start
    train_end = train_start + train_size
    validation_start = train_end + purge_size
    validation_end = validation_start + validation_size
    test_start = validation_end + purge_size
    test_end = test_start + test_size

    return ChronologicalSplit(
        train=tuple(samples[train_start:train_end]),
        validation=tuple(samples[validation_start:validation_end]),
        test=tuple(samples[test_start:test_end]),
    )


def binary_classification_metrics(records: Sequence[PredictionRecord]) -> dict[str, Decimal]:
    """Calculate deterministic OOS accuracy, precision, recall and Brier score."""
    if not records:
        raise ResearchValidationError("at least one prediction record is required.")
    if any(left.timestamp_ms >= right.timestamp_ms for left, right in pairwise(records)):
        raise ResearchValidationError("prediction records must be strictly chronological.")

    true_positive = sum(record.actual and record.predicted for record in records)
    false_positive = sum((not record.actual) and record.predicted for record in records)
    false_negative = sum(record.actual and (not record.predicted) for record in records)
    correct = sum(record.actual == record.predicted for record in records)
    total = Decimal(len(records))

    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    precision = (
        Decimal(true_positive) / Decimal(precision_denominator)
        if precision_denominator
        else Decimal("0")
    )
    recall = (
        Decimal(true_positive) / Decimal(recall_denominator) if recall_denominator else Decimal("0")
    )
    brier = (
        sum(
            (record.score - (Decimal("1") if record.actual else Decimal("0"))) ** 2
            for record in records
        )
        / total
    )

    return {
        "accuracy": Decimal(correct) / total,
        "precision": precision,
        "recall": recall,
        "brier_score": brier,
    }
