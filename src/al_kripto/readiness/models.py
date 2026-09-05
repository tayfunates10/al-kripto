"""Immutable models for the final production-readiness review gate."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_REFERENCE_PATTERN = re.compile(r"^(?:[a-z][a-z0-9+.-]*://\S{3,}|[0-9a-fA-F]{40})$")


class ReadinessValidationError(ValueError):
    """Raised when readiness evidence is ambiguous or malformed."""


class ReadinessStatus(StrEnum):
    """Possible outcomes of the automated readiness assessment."""

    NOT_READY = "not_ready"
    READY_FOR_MANUAL_REVIEW = "ready_for_manual_review"


class ReadinessCheck(StrEnum):
    """Evidence required before a human production review may begin."""

    PAPER_RUN_COMPLETE = "paper_run_complete"
    STRESS_TESTS_PASSED = "stress_tests_passed"
    TEST_ENV_EXECUTION_PASSED = "test_environment_execution_passed"
    CI_GREEN = "ci_green"
    RECONCILIATION_VERIFIED = "reconciliation_verified"
    MONITORING_HEALTHY = "monitoring_healthy"
    RISK_LIMITS_CONFIGURED = "risk_limits_configured"
    KILL_SWITCH_TESTED = "kill_switch_tested"
    SECRET_POLICY_VERIFIED = "secret_policy_verified"
    WITHDRAWALS_DISABLED = "withdrawals_disabled"
    ROLLBACK_PLAN_DOCUMENTED = "rollback_plan_documented"


REQUIRED_READINESS_CHECKS: tuple[ReadinessCheck, ...] = tuple(ReadinessCheck)


@dataclass(frozen=True, slots=True)
class ReadinessEvidence:
    """One auditable readiness claim plus a verifiable, time-bounded reference."""

    check: ReadinessCheck
    passed: bool
    reference: str
    recorded_at_ms: int
    valid_until_ms: int

    def __post_init__(self) -> None:
        if not _REFERENCE_PATTERN.fullmatch(self.reference.strip()):
            raise ReadinessValidationError(
                "evidence reference must be a URI-like reference or a 40-character commit SHA."
            )
        if self.recorded_at_ms < 0:
            raise ReadinessValidationError("recorded_at_ms must be >= 0.")
        if self.valid_until_ms <= self.recorded_at_ms:
            raise ReadinessValidationError("valid_until_ms must be later than recorded_at_ms.")


@dataclass(frozen=True, slots=True)
class ReadinessAssessment:
    """Fail-closed technical assessment that never enables live trading."""

    status: ReadinessStatus
    assessed_at_ms: int
    passed_checks: tuple[ReadinessCheck, ...]
    failed_checks: tuple[ReadinessCheck, ...]
    missing_checks: tuple[ReadinessCheck, ...]
    evidence: tuple[ReadinessEvidence, ...]

    def __post_init__(self) -> None:
        if self.assessed_at_ms < 0:
            raise ReadinessValidationError("assessed_at_ms must be >= 0.")
        passed = set(self.passed_checks)
        failed = set(self.failed_checks)
        missing = set(self.missing_checks)
        if passed & failed or passed & missing or failed & missing:
            raise ReadinessValidationError("readiness check groups must not overlap.")
        if self.status is ReadinessStatus.READY_FOR_MANUAL_REVIEW and (
            self.failed_checks or self.missing_checks
        ):
            raise ReadinessValidationError(
                "ready_for_manual_review cannot contain failed or missing checks."
            )
        if self.status is ReadinessStatus.NOT_READY and not (
            self.failed_checks or self.missing_checks
        ):
            raise ReadinessValidationError("not_ready requires failed or missing evidence.")
