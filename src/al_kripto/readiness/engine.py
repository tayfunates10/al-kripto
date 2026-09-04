"""Fail-closed technical readiness assessment without production activation."""

from __future__ import annotations

from collections.abc import Sequence

from .models import (
    REQUIRED_READINESS_CHECKS,
    ReadinessAssessment,
    ReadinessCheck,
    ReadinessEvidence,
    ReadinessStatus,
    ReadinessValidationError,
)


def assess_production_readiness(
    evidence: Sequence[ReadinessEvidence],
) -> ReadinessAssessment:
    """Assess technical evidence and stop at human review; never enable live trading."""
    by_check: dict[ReadinessCheck, ReadinessEvidence] = {}
    for item in evidence:
        if item.check in by_check:
            raise ReadinessValidationError(f"duplicate readiness evidence: {item.check.value}")
        by_check[item.check] = item

    passed_checks = tuple(
        check for check in REQUIRED_READINESS_CHECKS if check in by_check and by_check[check].passed
    )
    failed_checks = tuple(
        check for check in REQUIRED_READINESS_CHECKS if check in by_check and not by_check[check].passed
    )
    missing_checks = tuple(check for check in REQUIRED_READINESS_CHECKS if check not in by_check)

    status = (
        ReadinessStatus.READY_FOR_MANUAL_REVIEW
        if not failed_checks and not missing_checks
        else ReadinessStatus.NOT_READY
    )
    ordered_evidence = tuple(by_check[check] for check in REQUIRED_READINESS_CHECKS if check in by_check)

    return ReadinessAssessment(
        status=status,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
        missing_checks=missing_checks,
        evidence=ordered_evidence,
    )


def readiness_payload(assessment: ReadinessAssessment) -> dict[str, object]:
    """Return a JSON-safe audit payload that explicitly leaves live trading disabled."""
    return {
        "status": assessment.status.value,
        "live_trading_enabled": False,
        "next_action": (
            "manual_security_review"
            if assessment.status is ReadinessStatus.READY_FOR_MANUAL_REVIEW
            else "complete_missing_or_failed_evidence"
        ),
        "passed_checks": [check.value for check in assessment.passed_checks],
        "failed_checks": [check.value for check in assessment.failed_checks],
        "missing_checks": [check.value for check in assessment.missing_checks],
        "evidence": [
            {
                "check": item.check.value,
                "passed": item.passed,
                "reference": item.reference,
            }
            for item in assessment.evidence
        ],
    }
